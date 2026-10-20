package hebench

// Plaintext reference costs for the recommended on-device path (PROPOSAL.md):
// LDA projection + scaled-Manhattan score + AES-256-GCM seal/open of the template blob.
import (
	"crypto/aes"
	"crypto/cipher"
	"crypto/rand"
	"encoding/binary"
	"math"
	"testing"
)

const dFeat, dLDA = 36, 16

func vec(n int) []float64 {
	v := make([]float64, n)
	for i := range v {
		v[i] = float64(i%7) * 0.13
	}
	return v
}

func score(x, mu, sd, W []float64) float64 {
	var s float64
	for i := 0; i < dFeat; i++ {
		s += math.Abs(x[i]-mu[i]) / sd[i]
	}
	// LDA-16 projection (used by the second score)
	var e float64
	for j := 0; j < dLDA; j++ {
		var p float64
		for i := 0; i < dFeat; i++ {
			p += W[j*dFeat+i] * x[i]
		}
		e += p * p
	}
	return s/dFeat + 1e-12*e
}

func BenchmarkPlainScore(b *testing.B) {
	x, mu, sd, W := vec(dFeat), vec(dFeat), vec(dFeat), vec(dFeat*dLDA)
	for i := range sd {
		sd[i] += 1
	}
	var acc float64
	for i := 0; i < b.N; i++ {
		acc += score(x, mu, sd, W)
	}
	_ = acc
}

func blob() []byte { // template: mu, sd (36 each) + 4 anchors x 36, float64
	v := make([]byte, (2+4)*dFeat*8)
	for i := 0; i < len(v)/8; i++ {
		binary.LittleEndian.PutUint64(v[i*8:], math.Float64bits(float64(i)))
	}
	return v
}

func BenchmarkTemplateSealOpenAESGCM(b *testing.B) {
	key := make([]byte, 32)
	rand.Read(key)
	blk, _ := aes.NewCipher(key)
	g, _ := cipher.NewGCM(blk)
	pt := blob()
	nonce := make([]byte, g.NonceSize())
	b.SetBytes(int64(len(pt)))
	for i := 0; i < b.N; i++ {
		rand.Read(nonce)
		ct := g.Seal(nil, nonce, pt, []byte("ztbe/template/v2"))
		if _, err := g.Open(nil, nonce, ct, []byte("ztbe/template/v2")); err != nil {
			b.Fatal(err)
		}
	}
	b.ReportMetric(float64(len(pt)+g.Overhead()+g.NonceSize()), "sealed_B")
}
