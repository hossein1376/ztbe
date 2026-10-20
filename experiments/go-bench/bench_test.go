// Package bench contains micro-benchmarks used to sanity-check the latency and
// storage claims of ZTBE spec v1.0.0-draft (sections 4.3 B/C, 5.4, NFR-03/04).
// Run: go test -bench . -benchmem
package bench

import (
	"crypto/hkdf"
	"crypto/hmac"
	"crypto/rand"
	"crypto/sha256"
	"encoding/binary"
	"math/bits"
	mrand "math/rand/v2"
	"testing"
)

const (
	n      = 512 // bits in w
	kSub   = 32  // bits per locker subset
	rBytes = 32  // R (256-bit key, spec 5.4)
	gBytes = 8   // gamma = 64 zero-check bits
)

type locker struct {
	idx   [kSub]uint16 // explicit subset (64 B). Could instead be derived from a seed.
	nonce [16]byte
	ct    [rBytes + gBytes]byte
}

func subset(w []byte, idx *[kSub]uint16) []byte {
	var v [kSub / 8]byte
	for i, j := range idx {
		if w[j/8]>>(j%8)&1 == 1 {
			v[i/8] |= 1 << (i % 8)
		}
	}
	return v[:]
}

func padHKDF(nonce, v []byte) []byte {
	k, err := hkdf.Key(sha256.New, v, nonce, "ztbe-locker", rBytes+gBytes)
	if err != nil {
		panic(err)
	}
	return k
}

func padHMAC(nonce, v []byte) []byte { // single HMAC call; 32 B pad -> would need 2 calls for 40 B
	m := hmac.New(sha256.New, nonce)
	m.Write(v)
	a := m.Sum(nil)
	m.Reset()
	m.Write([]byte{1})
	m.Write(v)
	return append(a, m.Sum(nil)[:gBytes]...)
}

func gen(w []byte, ell int, pad func(a, b []byte) []byte) []locker {
	R := make([]byte, rBytes)
	rand.Read(R)
	L := make([]locker, ell)
	r := mrand.New(mrand.NewPCG(1, 2))
	for i := range L {
		p := r.Perm(n)
		for j := 0; j < kSub; j++ {
			L[i].idx[j] = uint16(p[j])
		}
		rand.Read(L[i].nonce[:])
		k := pad(L[i].nonce[:], subset(w, &L[i].idx))
		for j := range L[i].ct {
			var x byte
			if j < rBytes {
				x = R[j]
			}
			L[i].ct[j] = k[j] ^ x
		}
	}
	return L
}

// rep tries every locker (worst case = reject); returns true on first zero-pad match.
func rep(w []byte, L []locker, pad func(a, b []byte) []byte) bool {
	for i := range L {
		k := pad(L[i].nonce[:], subset(w, &L[i].idx))
		ok := true
		for j := rBytes; j < rBytes+gBytes; j++ {
			if k[j] != L[i].ct[j] {
				ok = false
				break
			}
		}
		if ok {
			return true
		}
	}
	return false
}

func randW() []byte { w := make([]byte, n/8); rand.Read(w); return w }

func benchRep(b *testing.B, ell int, pad func(a, b []byte) []byte) {
	L := gen(randW(), ell, pad)
	probe := randW() // unrelated -> worst case, all lockers tried
	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		rep(probe, L, pad)
	}
}

func BenchmarkRepHKDF_l1000(b *testing.B) { benchRep(b, 1000, padHKDF) }
func BenchmarkRepHKDF_l1500(b *testing.B) { benchRep(b, 1500, padHKDF) }
func BenchmarkRepHMAC_l1500(b *testing.B) { benchRep(b, 1500, padHMAC) }

// Bloom filter comparison: B=32 blocks x 2^Wb=256 bits (spec 5.3 example).
func BenchmarkBloomDistance(b *testing.B) {
	var A, Bf [32][4]uint64
	for r := range A {
		for j := range A[r] {
			A[r][j], Bf[r][j] = mrand.Uint64(), mrand.Uint64()
		}
	}
	b.ResetTimer()
	var s float64
	for i := 0; i < b.N; i++ {
		s = 0
		for r := range A {
			var x, wa, wb int
			for j := range A[r] {
				x += bits.OnesCount64(A[r][j] ^ Bf[r][j])
				wa += bits.OnesCount64(A[r][j])
				wb += bits.OnesCount64(Bf[r][j])
			}
			s += float64(x) / float64(wa+wb)
		}
	}
	_ = s
}

// Storage of one locker with explicit subsets vs seed-derived subsets.
func TestStorage(t *testing.T) {
	explicit := kSub*2 + 16 + rBytes + gBytes
	seeded := 16 + rBytes + gBytes // idx+nonce derived from (seed,i) via PRF; nonce kept for clarity
	minimal := rBytes + gBytes     // idx and nonce both derived from one public seed
	for _, ell := range []int{1000, 1500} {
		t.Logf("ell=%d: explicit %d B (%.1f KiB), nonce-only %d B (%.1f KiB), minimal %d B (%.1f KiB)",
			ell, ell*explicit, float64(ell*explicit)/1024, ell*seeded, float64(ell*seeded)/1024, ell*minimal, float64(ell*minimal)/1024)
	}
	_ = binary.LittleEndian
}
