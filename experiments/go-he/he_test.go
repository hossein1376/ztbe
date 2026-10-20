// Benchmarks for design-option evidence (notes/design-options.md):
//   - CKKS (lattigo v6): encrypted weighted squared-Euclidean distance between an
//     encrypted enrolled template and an encrypted probe (D features).
//   - BGV (lattigo v6): encrypted Hamming distance between encrypted bit templates.
//   - OPRF (circl, RFC 9497, ristretto255): server-side cost of a keyed (pepper) evaluation.
// Run: go test -run TestSizes -v -bench . -benchtime 20x
package hebench

import (
	"crypto/rand"
	"math"
	mrand "math/rand"
	"testing"

	"github.com/cloudflare/circl/oprf"
	"github.com/tuneinsight/lattigo/v6/core/rlwe"
	"github.com/tuneinsight/lattigo/v6/schemes/bgv"
	"github.com/tuneinsight/lattigo/v6/schemes/ckks"
)

const D = 64 // feature slots used (36 keystroke + 23 mouse features fit; padded to 64)

type ckksCtx struct {
	params ckks.Parameters
	ecd    *ckks.Encoder
	enc    *rlwe.Encryptor
	dec    *rlwe.Decryptor
	eval   *ckks.Evaluator
	sqrtW  *rlwe.Ciphertext // Enc(sqrt(w_j))       (template, stored server-side)
	muW    *rlwe.Ciphertext // Enc(mu_j*sqrt(w_j))  (template, stored server-side)
}

func newCKKS(tb testing.TB) (*ckksCtx, []float64, []float64, []float64) {
	params, err := ckks.NewParametersFromLiteral(ckks.ParametersLiteral{
		LogN: 13, LogQ: []int{50, 40, 40}, LogP: []int{50}, LogDefaultScale: 40,
	})
	if err != nil {
		tb.Fatal(err)
	}
	kgen := rlwe.NewKeyGenerator(params)
	sk, pk := kgen.GenKeyPairNew()
	rlk := kgen.GenRelinearizationKeyNew(sk)
	gks := kgen.GenGaloisKeysNew(params.GaloisElementsForInnerSum(1, D), sk)
	c := &ckksCtx{params: params, ecd: ckks.NewEncoder(params), enc: rlwe.NewEncryptor(params, pk),
		dec: rlwe.NewDecryptor(params, sk), eval: ckks.NewEvaluator(params, rlwe.NewMemEvaluationKeySet(rlk, gks...))}
	r := mrand.New(mrand.NewSource(1))
	mu, w, x := make([]float64, D), make([]float64, D), make([]float64, D)
	for j := range mu {
		mu[j] = r.NormFloat64()
		w[j] = 0.5 + r.Float64()
		x[j] = mu[j] + 0.3*r.NormFloat64()
	}
	sw, mw := make([]float64, D), make([]float64, D)
	for j := range w {
		sw[j] = math.Sqrt(w[j])
		mw[j] = mu[j] * sw[j]
	}
	c.sqrtW = c.encrypt(tb, sw)
	c.muW = c.encrypt(tb, mw)
	return c, mu, w, x
}

func (c *ckksCtx) encrypt(tb testing.TB, v []float64) *rlwe.Ciphertext {
	pt := ckks.NewPlaintext(c.params, c.params.MaxLevel())
	if err := c.ecd.Encode(v, pt); err != nil {
		tb.Fatal(err)
	}
	ct, err := c.enc.EncryptNew(pt)
	if err != nil {
		tb.Fatal(err)
	}
	return ct
}

// distance computes Enc(sum_j w_j (x_j - mu_j)^2) in slot 0.
func (c *ckksCtx) distance(tb testing.TB, ctX *rlwe.Ciphertext) *rlwe.Ciphertext {
	t, err := c.eval.MulRelinNew(ctX, c.sqrtW)
	if err != nil {
		tb.Fatal(err)
	}
	if err = c.eval.Rescale(t, t); err != nil {
		tb.Fatal(err)
	}
	mw := c.muW.CopyNew()
	c.eval.DropLevel(mw, mw.Level()-t.Level())
	if err = c.eval.Sub(t, mw, t); err != nil {
		tb.Fatal(err)
	}
	if err = c.eval.MulRelin(t, t, t); err != nil {
		tb.Fatal(err)
	}
	if err = c.eval.Rescale(t, t); err != nil {
		tb.Fatal(err)
	}
	out := t.CopyNew()
	if err = c.eval.InnerSum(t, 1, D, out); err != nil {
		tb.Fatal(err)
	}
	return out
}

func (c *ckksCtx) decrypt(ct *rlwe.Ciphertext) float64 {
	v := make([]float64, c.params.MaxSlots())
	_ = c.ecd.Decode(c.dec.DecryptNew(ct), v)
	return v[0]
}

func TestCKKSCorrect(t *testing.T) {
	c, mu, w, x := newCKKS(t)
	got := c.decrypt(c.distance(t, c.encrypt(t, x)))
	want := 0.0
	for j := range x {
		want += w[j] * (x[j] - mu[j]) * (x[j] - mu[j])
	}
	if math.Abs(got-want) > 1e-3*math.Max(1, want) {
		t.Fatalf("got %v want %v", got, want)
	}
	t.Logf("CKKS distance ok: got %.6f want %.6f", got, want)
}

func TestSizes(t *testing.T) {
	c, _, _, x := newCKKS(t)
	ct := c.encrypt(t, x)
	b, _ := ct.MarshalBinary()
	t.Logf("CKKS logN=13 logQP=%.0f: fresh ciphertext %d B; stored template (2 ct) %d B", c.params.LogQP(), len(b), 2*len(b))
	res := c.distance(t, ct)
	rb, _ := res.MarshalBinary()
	t.Logf("CKKS result ciphertext (level %d) %d B", res.Level(), len(rb))
	kgen := rlwe.NewKeyGenerator(c.params)
	sk := kgen.GenSecretKeyNew()
	rlk := kgen.GenRelinearizationKeyNew(sk)
	gks := kgen.GenGaloisKeysNew(c.params.GaloisElementsForInnerSum(1, D), sk)
	kb, _ := rlk.MarshalBinary()
	tot := len(kb)
	for _, g := range gks {
		gb, _ := g.MarshalBinary()
		tot += len(gb)
	}
	t.Logf("CKKS evaluation keys (relin + %d Galois) %d B", len(gks), tot)
	bp, bct := newBGV(t)
	bb, _ := bct.MarshalBinary()
	t.Logf("BGV logN=%d logQP=%.0f: bit-template ciphertext %d B", bp.params.LogN(), bp.params.LogQP(), len(bb))
}

func BenchmarkCKKSClientEncrypt(b *testing.B) {
	c, _, _, x := newCKKS(b)
	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		c.encrypt(b, x)
	}
}

func BenchmarkCKKSServerDistance(b *testing.B) {
	c, _, _, x := newCKKS(b)
	ct := c.encrypt(b, x)
	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		c.distance(b, ct)
	}
}

func BenchmarkCKKSDecrypt(b *testing.B) {
	c, _, _, x := newCKKS(b)
	res := c.distance(b, c.encrypt(b, x))
	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		c.decrypt(res)
	}
}

func BenchmarkCKKSKeygen(b *testing.B) {
	for i := 0; i < b.N; i++ {
		newCKKS(b)
	}
}

// ---------------------------------------------------------------- BGV Hamming distance
type bgvCtx struct {
	params bgv.Parameters
	ecd    *bgv.Encoder
	enc    *rlwe.Encryptor
	eval   *bgv.Evaluator
	tmpl   *rlwe.Ciphertext
	probe  *rlwe.Ciphertext
	dec    *rlwe.Decryptor
	nbits  int
	want   uint64
}

func newBGV(tb testing.TB) (*bgvCtx, *rlwe.Ciphertext) {
	params, err := bgv.NewParametersFromLiteral(bgv.ParametersLiteral{
		LogN: 13, LogQ: []int{54, 54}, LogP: []int{55}, PlaintextModulus: 65537,
	})
	if err != nil {
		tb.Fatal(err)
	}
	kgen := rlwe.NewKeyGenerator(params)
	sk, pk := kgen.GenKeyPairNew()
	rlk := kgen.GenRelinearizationKeyNew(sk)
	n := 256
	gks := kgen.GenGaloisKeysNew(params.GaloisElementsForInnerSum(1, n), sk)
	c := &bgvCtx{params: params, ecd: bgv.NewEncoder(params), enc: rlwe.NewEncryptor(params, pk),
		eval: bgv.NewEvaluator(params, rlwe.NewMemEvaluationKeySet(rlk, gks...)), dec: rlwe.NewDecryptor(params, sk), nbits: n}
	r := mrand.New(mrand.NewSource(2))
	t, p := make([]uint64, n), make([]uint64, n)
	for i := range t {
		t[i] = uint64(r.Intn(2))
		p[i] = t[i]
		if r.Float64() < 0.2 {
			p[i] ^= 1
		}
		c.want += t[i] ^ p[i]
	}
	enc := func(v []uint64) *rlwe.Ciphertext {
		pt := bgv.NewPlaintext(params, params.MaxLevel())
		if err := c.ecd.Encode(v, pt); err != nil {
			tb.Fatal(err)
		}
		ct, err := c.enc.EncryptNew(pt)
		if err != nil {
			tb.Fatal(err)
		}
		return ct
	}
	c.tmpl, c.probe = enc(t), enc(p)
	return c, c.tmpl
}

// hamming: HD = sum t + p - 2tp
func (c *bgvCtx) hamming(tb testing.TB) *rlwe.Ciphertext {
	tp, err := c.eval.MulRelinNew(c.tmpl, c.probe)
	if err != nil {
		tb.Fatal(err)
	}
	if err = c.eval.Mul(tp, 2, tp); err != nil {
		tb.Fatal(err)
	}
	s, err := c.eval.AddNew(c.tmpl, c.probe)
	if err != nil {
		tb.Fatal(err)
	}
	if err = c.eval.Sub(s, tp, s); err != nil {
		tb.Fatal(err)
	}
	out := s.CopyNew()
	if err = c.eval.InnerSum(s, 1, c.nbits, out); err != nil {
		tb.Fatal(err)
	}
	return out
}

func TestBGVCorrect(t *testing.T) {
	c, _ := newBGV(t)
	res := c.hamming(t)
	v := make([]uint64, c.params.MaxSlots())
	_ = c.ecd.Decode(c.dec.DecryptNew(res), v)
	t.Logf("BGV encrypted Hamming distance over %d bits = %d", c.nbits, v[0])
	if v[0] != c.want {
		t.Fatalf("HD mismatch: got %d want %d", v[0], c.want)
	}
}

func BenchmarkBGVServerHamming256(b *testing.B) {
	c, _ := newBGV(b)
	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		c.hamming(b)
	}
}

// ---------------------------------------------------------------- OPRF (pepper / HSM-style keyed evaluation)
func BenchmarkOPRFServerEvaluateRistretto(b *testing.B) {
	sk, _ := oprf.GenerateKey(oprf.SuiteRistretto255, rand.Reader)
	srv := oprf.NewServer(oprf.SuiteRistretto255, sk)
	cl := oprf.NewClient(oprf.SuiteRistretto255)
	_, req, _ := cl.Blind([][]byte{[]byte("template-digest")})
	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		if _, err := srv.Evaluate(req); err != nil {
			b.Fatal(err)
		}
	}
}

func BenchmarkOPRFClientRoundTripRistretto(b *testing.B) {
	sk, _ := oprf.GenerateKey(oprf.SuiteRistretto255, rand.Reader)
	srv := oprf.NewServer(oprf.SuiteRistretto255, sk)
	cl := oprf.NewClient(oprf.SuiteRistretto255)
	for i := 0; i < b.N; i++ {
		fin, req, _ := cl.Blind([][]byte{[]byte("template-digest")})
		ev, _ := srv.Evaluate(req)
		if _, err := cl.Finalize(fin, ev); err != nil {
			b.Fatal(err)
		}
	}
}
