package hebench

// Cost of signing/verifying a ~200-byte risk assertion (software keys; TPM/Secure Enclave latency not measured).
import (
	"crypto/ecdsa"
	"crypto/ed25519"
	"crypto/elliptic"
	"crypto/rand"
	"crypto/sha256"
	"testing"
)

var assertion = make([]byte, 200)

func BenchmarkAssertionSignEd25519(b *testing.B) {
	_, sk, _ := ed25519.GenerateKey(rand.Reader)
	for i := 0; i < b.N; i++ {
		_ = ed25519.Sign(sk, assertion)
	}
}

func BenchmarkAssertionVerifyEd25519(b *testing.B) {
	pk, sk, _ := ed25519.GenerateKey(rand.Reader)
	sig := ed25519.Sign(sk, assertion)
	for i := 0; i < b.N; i++ {
		if !ed25519.Verify(pk, assertion, sig) {
			b.Fatal("bad")
		}
	}
}

func BenchmarkAssertionSignP256(b *testing.B) {
	sk, _ := ecdsa.GenerateKey(elliptic.P256(), rand.Reader)
	h := sha256.Sum256(assertion)
	for i := 0; i < b.N; i++ {
		_, _ = ecdsa.SignASN1(rand.Reader, sk, h[:])
	}
}

func BenchmarkAssertionVerifyP256(b *testing.B) {
	sk, _ := ecdsa.GenerateKey(elliptic.P256(), rand.Reader)
	h := sha256.Sum256(assertion)
	sig, _ := ecdsa.SignASN1(rand.Reader, sk, h[:])
	for i := 0; i < b.N; i++ {
		if !ecdsa.VerifyASN1(&sk.PublicKey, h[:], sig) {
			b.Fatal("bad")
		}
	}
}
