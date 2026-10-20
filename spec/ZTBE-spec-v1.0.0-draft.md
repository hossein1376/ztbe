# **Product & Mathematical Specification: ZeroTrace Behavioral Engine (ZTBE)**

**Version:** 1.0.0-draft **Classification:** Open-Source Reference Architecture & Mathematical Specification **Compliance Targets:** ISO/IEC 24745:2022 (Biometric Information Protection), ISO/IEC 30136:2018 (Performance Testing of Biometric Template Protection), GDPR Articles 9 & 25 (Data Protection by Design and by Default)

## **1\. Executive Summary & Problem Statement**

### **1.1 Product Vision**

**ZeroTrace Behavioral Engine (ZTBE)** is a lightweight, Free and Open-Source Software (FOSS) behavioral profiling and continuous verification engine. It passively observes user interaction telemetry—including keystroke dynamics, mouse kinematics, UI interaction rhythms, and web browsing navigation patterns—to construct an evolving behavioral signature for each user.

### **1.2 The Core Cryptographic Paradox**

Traditional behavioral biometrics systems store raw statistical feature vectors (e.g., mean digraph latencies, mouse velocity distributions, or neural network embeddings) in plaintext or reversibly encrypted databases. If the database is compromised or subpoenaed, the raw profiles can be inverted to reconstruct sensitive user habits, typing speeds, physical impairments, or browsing workflows.  
Conversely, standard cryptographic hash functions (such as \\text{SHA-256} or \\text{Argon2}) cannot be applied directly to behavioral profiles due to the **avalanche effect**: flipping a single input bit randomizes roughly 50\\% of the output bits. Because human behavior exhibits natural intra-subject variance (typically 5\\% to 20\\% fluctuation across sessions due to fatigue, posture, or hardware changes), two behavioral samples from the same user will never be bit-for-bit identical:  
w' \\neq w \\implies \\text{SHA-256}(w') \\neq \\text{SHA-256}(w)  
Furthermore, human habits exhibit **concept drift** over time (e.g., gradual typing speed improvements, learning new software shortcuts, or adapting to a new mouse). Updating a profile continuously normally requires access to the underlying feature distribution, which conflicts with the requirement that the stored profile be **mathematically irreversible**.  
ZTBE resolves this tension by combining **single-pass streaming statistical estimators** (O(1) memory complexity) with **Biometric Template Protection (BTP)** primitives—specifically **Reusable Fuzzy Extractors (RFE)**, **Error-Correcting Code-Offset Syndromes**, and **Cancelable Adaptive Bloom Filters**—governed by an authenticated ephemeral adaptation loop.

## **2\. Product Requirements Specification (PRD)**

### **2.1 Functional Requirements**

| ID | Requirement Name | Description | Priority |
| :---- | :---- | :---- | :---- |
| **FR-01** | **Multi-Modal Telemetry Ingestion** | Capture asynchronous interaction events across four modalities: (1) Keystroke timings, (2) Pointer/mouse kinematics, (3) UI click/scroll cadence, and (4) Web/DOM navigation state transitions. | **P0** |
| **FR-02** | **Content-Blind Privacy Filtering** | Telemetry collectors must strip actual alphanumeric characters and URL payloads at capture time, substituting character classes (e.g., ALPHA\_LEFT, NUMPAD, BACKSPACE) and hashed DOM/route categories prior to feature extraction. | **P0** |
| **FR-03** | **Online Streaming Feature Extraction** | Transform raw event streams into normalized, fixed-dimension feature vectors \\mathbf{x}^{(t)} \\in \\mathbb{R}^d incrementally on each event without storing historical event logs. | **P0** |
| **FR-04** | **Irreversible Profile Hashing** | Transform the behavioral profile into a protected reference \\mathcal{T} \= (P, H(R)) or cancelable binary template \\mathbf{B} such that computing a realistic behavioral feature vector \\hat{\\mathbf{x}} from \\mathcal{T} is computationally or information-theoretically infeasible. | **P0** |
| **FR-05** | **Noisy Verification (Verify)** | Given a fresh behavioral window vector \\mathbf{x}' and stored irreversible profile \\mathcal{T}, output a binary verification decision d \\in \\{0, 1\\} and a continuous trust score S\_{\\text{trust}} \\in \[0, 1\] whenever the distance \\text{dist}(\\mathbf{x}, \\mathbf{x}') \\le t. | **P0** |
| **FR-06** | **(Semi-)Continuous Drift Adaptation** | Dynamically adjust the user's protected profile to accommodate gradual habit drift (\\Delta \\mathbf{x}) while preventing both helper-data correlation leakage and adversarial poisoning. | **P0** |
| **FR-07** | **Unlinkability & Revocability** | Support per-application or per-deployment salts/keys so that two profiles of the same user across different databases are statistically independent, and compromised templates can be re-issued. | **P1** |

### **2.2 Non-Functional & Hardware Resource Requirements**

| ID | Metric | Target Constraint | Rationale |
| :---- | :---- | :---- | :---- |
| **NFR-01** | **Memory Footprint (RAM)** | \\le 15\\text{ MB} base daemon footprint; \\le 4\\text{ KB} ephemeral state per active user session. | Must run smoothly on edge devices, browser workers, or high-density multi-tenant servers. |
| **NFR-02** | **CPU Utilization** | \\le 1.5\\% of a single 2.0\\text{ GHz} vCPU core during continuous typing/browsing (20\\text{ events/sec}). | Eliminates battery drain on laptops/mobile devices and avoids UI input lag. |
| **NFR-03** | **Verification & Hash Latency** | \\le 2\\text{ ms} for feature extraction; \\le 8\\text{ ms} for Fuzzy Extractor reproduction (\\text{Rep}) or Bloom filter comparison. | Enables real-time continuous authentication on every interaction window. |
| **NFR-04** | **Persistent Storage Size** | \\le 2\\text{ KB} per user profile on disk/database. | Facilitates fast retrieval and minimal database bloat. |
| **NFR-05** | **Zero Raw Persistence** | 0\\text{ bytes} of raw behavioral timings or plaintext feature vectors written to non-volatile storage or swap space. | Protects against cold-boot, disk-forensic, and database dump breaches. |

## **3\. Mathematical Foundation of Behavioral Feature Extraction & Streaming Profiling**

To satisfy **NFR-01** and **NFR-05**, ZTBE processes incoming events as an infinite stream e\_1, e\_2, \\dots, e\_k, \\dots and maintains rolling statistics in O(1) space.

### **3.1 Multi-Modal Behavioral Feature Space**

A behavioral window W\_k consists of N\_w consecutive interaction events (or a fixed time horizon \\Delta T\_w, e.g., 30\\text{ seconds} of active interaction). From W\_k, the engine extracts a d-dimensional continuous feature vector \\mathbf{x} \\in \\mathbb{R}^d partitioned into four sub-vectors:

\\mathbf{x} \= \\left\[ \\mathbf{x}\_{\\text{key}} \\;\\Vert\\; \\mathbf{x}\_{\\text{mouse}} \\;\\Vert\\; \\mathbf{x}\_{\\text{nav}} \\;\\Vert\\; \\mathbf{x}\_{\\text{temporal}} \\right\]^T

#### **1\. Keystroke Dynamics (\\mathbf{x}\_{\\text{key}})**

For a sequence of key press timestamps t\_i^{\\text{down}} and release timestamps t\_i^{\\text{up}} mapped to C privacy-preserving key zones (e.g., left-hand home row, right-hand top row, modifiers, backspace):

> * **Hold / Dwell Time (H\_i):** H\_i \= t\_i^{\\text{up}} \- t\_i^{\\text{down}}  
> * **Press-to-Press Digraph Latency (PP\_{i,i+1}):** PP\_{i,i+1} \= t\_{i+1}^{\\text{down}} \- t\_i^{\\text{down}}  
> * **Release-to-Press Flight Time (RP\_{i,i+1}):** RP\_{i,i+1} \= t\_{i+1}^{\\text{down}} \- t\_i^{\\text{up}} *(Note: RP\_{i,i+1} \< 0 captures rollover typing, a highly discriminative habitual trait where the user presses the next key before releasing the previous key).*  
> * **Error-Correction Habit Ratio (R\_{\\text{err}}):** The ratio of destructive keystrokes (BACKSPACE, DELETE, CTRL+Z) to total keystrokes within the window.

#### **2\. Mouse & Pointer Kinematics (\\mathbf{x}\_{\\text{mouse}})**

Given discrete pointer coordinates (u\_i, v\_i) sampled at timestamps t\_i, define spatial displacement \\delta s\_i \= \\sqrt{(u\_i \- u\_{i-1})^2 \+ (v\_i \- v\_{i-1})^2} and time step \\delta t\_i \= t\_i \- t\_{i-1}:

> * **Instantaneous Velocity, Acceleration, and Jerk:** v\_i \= \\frac{\\delta s\_i}{\\delta t\_i}, \\quad a\_i \= \\frac{v\_i \- v\_{i-1}}{\\delta t\_i}, \\quad j\_i \= \\frac{a\_i \- a\_{i-1}}{\\delta t\_i}  
> * **Trajectory Straightness / Curvature Efficiency (\\eta\_{\\text{path}}):** For a ballistic sub-movement from point A \= (u\_0, v\_0) to click target B \= (u\_M, v\_M): \\eta\_{\\text{path}} \= \\frac{\\sqrt{(u\_M \- u\_0)^2 \+ (v\_M \- v\_0)^2}}{\\sum\_{i=1}^{M} \\delta s\_i} \\in (0, 1\]  
> * **Fitts's Law Index of Performance (IP):** Relating movement duration MT to target distance D and effective target width W\_e: IP \= \\frac{\\log\_2\\left(\\frac{D}{W\_e} \+ 1\\right)}{MT}  
> * **Click Dwell & Double-Click Interval Distributions:** Mean and variance of mouse button hold duration t\_i^{\\text{mouse\\\_up}} \- t\_i^{\\text{mouse\\\_down}}.

#### **3\. Web Browsing & UI Navigation Habits (\\mathbf{x}\_{\\text{nav}})**

User browsing and application workflows are modeled as transitions over a finite state space of K abstract interaction states \\mathcal{S} \= \\{s\_1, s\_2, \\dots, s\_K\\} (e.g., SEARCH\_INPUT, LINK\_CLICK, TAB\_SWITCH, SCROLL\_READ, FORM\_SUBMIT, BACK\_NAV):

> * **First-Order Markov Transition Probabilities:** A flattened stochastic transition matrix M \\in \[0, 1\]^{K \\times K} where entry M\_{a,b} \= \\Pr(S\_{t+1} \= s\_b \\mid S\_t \= s\_a).  
> * **Navigation Entropy (H\_{\\text{nav}}):** Captures whether a user exhibits rigid, repetitive workflows versus exploratory browsing: H\_{\\text{nav}} \= \-\\sum\_{a=1}^{K} \\pi\_a \\sum\_{b=1}^{K} M\_{a,b} \\log\_2(M\_{a,b}) where \\boldsymbol{\\pi} is the stationary distribution of state visitation frequencies.

#### **4\. Circadian & Burst Cadence (\\mathbf{x}\_{\\text{temporal}})**

> * **Inter-Event Burstiness (B\_{\\text{event}}):** Given mean inter-arrival time \\mu\_{\\tau} and standard deviation \\sigma\_{\\tau}: B\_{\\text{event}} \= \\frac{\\sigma\_{\\tau} \- \\mu\_{\\tau}}{\\sigma\_{\\tau} \+ \\mu\_{\\tau}} \\in \[-1, 1\]  
> * **Circular Time-of-Day Encoding:** Active session timestamps t\_{\\text{day}} \\in \[0, 86400\) are projected onto the unit circle via \\sin(2\\pi t\_{\\text{day}} / 86400\) and \\cos(2\\pi t\_{\\text{day}} / 86400\) to preserve continuity across midnight.

### **3.2 Streaming O(1) Feature Accumulation (Exponentially Weighted Welford Algorithm)**

Within an active session window, features are updated one event at a time without keeping an array of past events. For each scalar feature x\_j (j \\in \\{1, \\dots, d\\}) and decay factor \\alpha \\in (0, 1\) (where \\alpha \= 2 / (N\_{\\text{eff}} \+ 1\) controls the effective memory horizon):  
\\delta\_j^{(k)} \= x\_j^{(k)} \- \\mu\_j^{(k-1)} \\mu\_j^{(k)} \= \\mu\_j^{(k-1)} \+ \\alpha \\delta\_j^{(k)} (\\sigma\_j^2)^{(k)} \= (1 \- \\alpha) \\left( (\\sigma\_j^2)^{(k-1)} \+ \\alpha \\left(\\delta\_j^{(k)}\\right)^2 \\right)  
Both the exponentially weighted moving mean \\mu\_j^{(k)} and moving standard deviation \\sigma\_j^{(k)} \= \\sqrt{(\\sigma\_j^2)^{(k)}} are retained as distinct coordinates in the consolidated window vector \\mathbf{z} \\in \\mathbb{R}^{2d}, since a user's behavioral consistency (\\sigma\_j) is as discriminative as their speed (\\mu\_j).

## **4\. The Mathematics of Behavioral Hashing (Irreversible Profile Construction)**

To ensure that a stored profile cannot be inverted to reveal \\mathbf{z}, ZTBE transforms the continuous vector \\mathbf{z} \\in \\mathbb{R}^D (D \= 2d) into an irreversible cryptographic artifact.

### **4.1 Why Locality-Sensitive Hashing (LSH) Alone Is Insufficient**

A common misconception is that Locality-Sensitive Hashing (such as \\text{SimHash} or \\text{MinHash}) provides privacy because it projects vectors onto binary strings via random hyperplanes:  
h\_{\\mathbf{r}}(\\mathbf{z}) \= \\text{sgn}(\\mathbf{r}^T \\mathbf{z})  
**Security Flaw:** By definition, LSH preserves cosine or Euclidean similarity in the output Hamming space:  
d\_H(\\text{LSH}(\\mathbf{z}\_1), \\text{LSH}(\\mathbf{z}\_2)) \\propto \\theta(\\mathbf{z}\_1, \\mathbf{z}\_2)  
If an attacker obtains the stored LSH digest \\mathbf{y} \= \\text{LSH}(\\mathbf{z}) and the hyperplane matrix \\mathbf{R} (or queries a verification oracle), they can formulate a convex feasibility or linear programming problem (\\mathbf{R}\_i \\hat{\\mathbf{z}} \\ge 0 for y\_i \= 1, \\mathbf{R}\_i \\hat{\\mathbf{z}} \< 0 for y\_i \= 0\) or apply hill-climbing gradient inversion to reconstruct an estimate \\hat{\\mathbf{z}} arbitrarily close to the true user habits \\mathbf{z}. Therefore, **LSH must never be stored directly as the terminal profile**.

### **4.2 Stage 1: Reliability-Weighted Equal-Probability Quantization**

Before applying cryptographic template protection, the continuous vector \\mathbf{z} \\in \\mathbb{R}^D must be mapped into a binary string w \\in \\{0, 1\\}^n that maximizes inter-subject entropy while minimizing intra-subject bit flips.

> 1. **Population Background Normalization:** Let \\boldsymbol{\\mu}\_{\\text{pop}} \\in \\mathbb{R}^D and \\boldsymbol{\\sigma}\_{\\text{pop}} \\in \\mathbb{R}^D be global population priors (pre-computed offline from public datasets). Each feature z\_j is standardized: \\tilde{z}\_j \= \\frac{z\_j \- \\mu\_{\\text{pop}, j}}{\\sigma\_{\\text{pop}, j}}  
> 2. **Equal-Probability Interval Partitioning:** Assuming \\tilde{z}\_j \\sim \\mathcal{N}(0, 1\) across the population, the real line is partitioned into 2^m equiprobable intervals I\_1, I\_2, \\dots, I\_{2^m} using the inverse Gaussian cumulative distribution function \\Phi^{-1}: \\beta\_q \= \\Phi^{-1}\\left(\\frac{q}{2^m}\\right), \\quad q \\in \\{1, \\dots, 2^m \- 1\\} Because each bin has probability 2^{-m}, the resulting quantized indices maximize Shannon entropy across the user population.  
> 3. **Gray Code Binary Mapping:** Each interval index q \\in \\{0, \\dots, 2^m \- 1\\} is encoded using an m-bit **reflected binary Gray code** \\mathcal{G}(q) \\in \\{0, 1\\}^m: \\mathcal{G}(q) \= q \\oplus \\lfloor q / 2 \\rfloor This guarantees that if a user's habit drifts into an adjacent quantization bin (q \\rightarrow q \\pm 1), **only 1 bit out of m flips**, bounding the Hamming error rate. Concatenating all D features yields an n-bit behavioral binary string w \\in \\{0, 1\\}^n, where n \= D \\cdot m.  
> 4. **Feature Reliability Masking (Optional Helper Bitmask M\_{\\text{rel}}):** During initial enrollment, features with high personal consistency (low intra-user variance relative to population variance, measured via Fisher's Discriminant Ratio FDR\_j \= \\frac{(\\mu\_{u,j} \- \\mu\_{\\text{pop},j})^2}{\\sigma\_{u,j}^2}) are selected, while noisy features are masked out.

### **4.3 Stage 2: Cryptographic Profile Hashing Architectures**

ZTBE supports three configurable mathematical backends for converting w \\in \\{0, 1\\}^n into an irreversible template, depending on the deployment threat model.

#### **Architecture A: Syndrome-Based Fuzzy Commitment / Fuzzy Extractor (Information-Theoretic Sketch)**

Based on Juels & Wattenberg (1999) and Dodis et al. (2004/2008), this scheme uses an \[n, k, 2t+1\] binary error-correcting linear code \\mathcal{C} (such as a **BCH code**, **Reed-Solomon code**, or **Polar code**) capable of correcting up to t bit flips in an n-bit string.

> * **Enrollment / Generation (\\text{Gen}(w) \\rightarrow (P, H\_{\\text{profile}})):**  
  1. Sample a uniform random codeword c \\xleftarrow{\\\$} \\mathcal{C} \\subset \\{0, 1\\}^n (corresponding to a random message m\_{\\text{sec}} \\in \\{0, 1\\}^k) and a random cryptographic salt s \\xleftarrow{\\\$} \\{0, 1\\}^{128}.  
  2. Compute the **Code-Offset Sketch** (or equivalently, the parity-check syndrome): P\_{\\text{sketch}} \= w \\oplus c \\quad \\text{(or } P\_{\\text{syn}} \= \\mathbf{H}\_{\\mathcal{C}} w^T \\in \\{0, 1\\}^{n-k}\\text{)} where \\mathbf{H}\_{\\mathcal{C}} is the (n-k) \\times n parity-check matrix of \\mathcal{C} satisfying \\mathbf{H}\_{\\mathcal{C}} c^T \= \\mathbf{0}.  
  3. Extract a uniform cryptographic key R \= \\text{Ext}(w; s) \\in \\{0, 1\\}^\\lambda using a universal hash function (e.g., \\text{HMAC-SHA256}(s, w) or Toeplitz matrix multiplication) and hash it via a one-way cryptographic hash: H\_{\\text{profile}} \= \\text{SHA-256}(R)  
  4. **Stored Profile:** Persist \\mathcal{T} \= (P\_{\\text{syn}}, s, H\_{\\text{profile}}) and immediately zero out w, c, R from RAM.  
> * **Verification (\\text{Rep}(w', \\mathcal{T}) \\rightarrow \\{0, 1\\}):**  
  1. Given a new behavioral observation w' \= w \\oplus e (where e \\in \\{0, 1\\}^n is the behavioral noise vector), compute the syndrome difference: \\Delta\_{\\text{syn}} \= \\mathbf{H}\_{\\mathcal{C}} (w')^T \\oplus P\_{\\text{syn}} \= \\mathbf{H}\_{\\mathcal{C}} (w \\oplus e)^T \\oplus \\mathbf{H}\_{\\mathcal{C}} w^T \= \\mathbf{H}\_{\\mathcal{C}} e^T  
  2. Run the bounded-distance syndrome decoder \\text{Decode}\_{\\mathcal{C}}(\\Delta\_{\\text{syn}}) \\rightarrow \\hat{e}.  
  3. If the Hamming weight \\text{wt}(e) \= d\_H(w, w') \\le t, then \\hat{e} \= e. Recover the exact enrolled behavioral vector in ephemeral memory: \\hat{w} \= w' \\oplus \\hat{e} \= (w \\oplus e) \\oplus e \= w  
  4. Recompute \\hat{R} \= \\text{Ext}(\\hat{w}; s) and check if \\text{SHA-256}(\\hat{R}) \\stackrel{?}{=} H\_{\\text{profile}}.  
  5. Additionally, the exact Hamming distance \\text{wt}(\\hat{e}) provides a continuous **Trust Score**: S\_{\\text{trust}} \= \\max\\left(0, \\; 1 \- \\frac{\\text{wt}(\\hat{e})}{t}\\right)  
> * **Irreversibility Guarantee (Min-Entropy Bound):** If the behavioral distribution W has min-entropy H\_\\infty(W) \= \-\\log\_2 \\max\_w \\Pr\[W \= w\] \= \\beta, publishing the (n-k)-bit syndrome P\_{\\text{syn}} reduces the conditional min-entropy to at least: \\tilde{H}\_\\infty(W \\mid P\_{\\text{syn}}) \\ge \\beta \- (n \- k) Provided \\beta \- (n \- k) \\ge \\lambda\_{\\text{sec}} (e.g., \\ge 80\\text{ bits}), P\_{\\text{syn}} is underdetermined by k dimensions (2^k valid pre-images exist in \\{0, 1\\}^n), and reversing \\mathcal{T} to recover w is information-theoretically impossible.

#### **Architecture B: Reusable Fuzzy Extractors via Sample-then-Lock (Computational Security)**

Standard code-offset sketches suffer from two practical limitations for behavioral profiles:

> 1. High error rates (15\\%–25\\% bit flips) degrade the code rate k/n due to the Gilbert-Varshamov and Plotkin bounds.  
> 2. **Boyen's Reusability Vulnerability (2004):** If a user's template is re-enrolled multiple times over correlated behavioral readings w^{(1)}, w^{(2)}, \\dots, w^{(\\rho)}, publishing multiple linear syndromes P^{(1)} \= \\mathbf{H}\_{\\mathcal{C}} w^{(1)}, P^{(2)} \= \\mathbf{H}\_{\\mathcal{C}} w^{(2)} allows an attacker to XOR helper strings and exploit linear correlations.

To support **repeated continuous re-hashing** and **low-entropy/oversampled behavioral features**, ZTBE implements the **Sample-then-Lock Reusable Fuzzy Extractor** (Canetti, Fuller, Paneth, Varia, 2016/2021):

> * **Enrollment (\\text{Gen}(w) \\rightarrow (P, H\_{\\text{profile}})):**  
  1. Sample a random secret seed R \\xleftarrow{\\\$} \\{0, 1\\}^\\lambda.  
  2. For \\ell independent iterations (i \= 1, \\dots, \\ell):  
     * Sample a random subset of k\_{\\text{sub}} bit indices \\mathcal{I}\_i \= \\{j\_{i,1}, j\_{i,2}, \\dots, j\_{i,k\_{\\text{sub}}}\\} \\subset \\{1, \\dots, n\\}.  
     * Extract the sub-string v\_i \= w\\vert{}\_{\\mathcal{I}\_i} \= (w\_{j\_{i,1}}, \\dots, w\_{j\_{i,k\_{\\text{sub}}}}) \\in \\{0, 1\\}^{k\_{\\text{sub}}}.  
     * Sample a random nonce \\text{nonce}\_i \\xleftarrow{\\\$} \\{0, 1\\}^{\\eta} and lock R inside a **Digital Locker** (symmetric encryption with zero-padding verification): c\_i \= \\text{Enc}\_{v\_i}(R \\;\\Vert\\; 0^\\gamma; \\text{nonce}\_i) \= \\text{HKDF}(\\text{nonce}\_i, v\_i) \\oplus (R \\;\\Vert\\; 0^\\gamma)  
  3. Set public helper data P \= \\{(\\mathcal{I}\_i, \\text{nonce}\_i, c\_i)\\}\_{i=1}^\\ell and store \\mathcal{T} \= (P, \\text{SHA-256}(R)).  
> * **Verification (\\text{Rep}(w', P)):**  
  1. Given w' \\in \\{0, 1\\}^n with Hamming distance d\_H(w, w') \\le t, iterate i \= 1, \\dots, \\ell:  
     * Extract v'\_i \= w'\\vert{}\_{\\mathcal{I}\_i}.  
     * Compute \\text{ candidate}\_i \= c\_i \\oplus \\text{HKDF}(\\text{nonce}\_i, v'\_i).  
     * If the trailing \\gamma bits of \\text{candidate}\_i are all zeros (0^\\gamma), output the prefix \\hat{R} and verify \\text{SHA-256}(\\hat{R}) \\stackrel{?}{=} H\_{\\text{profile}}.  
> * **Mathematical Correctness & Complexity:** The probability that a single random subset of size k\_{\\text{sub}} avoids all t flipped bits is bounded by: p\_{\\text{clean}} \= \\frac{\\binom{n \- t}{k\_{\\text{sub}}}}{\\binom{n}{k\_{\\text{sub}}}} \\approx \\left(1 \- \\frac{t}{n}\\right)^{k\_{\\text{sub}}} Choosing \\ell lockers ensures the false rejection probability \\delta\_{\\text{FRR}} (the chance that *none* of the \\ell subsets match cleanly) is bounded by: \\delta\_{\\text{FRR}} \= (1 \- p\_{\\text{clean}})^\\ell \\le \\exp\\left(-\\ell \\left(1 \- \\frac{t}{n}\\right)^{k\_{\\text{sub}}}\\right) *Example:* For n \= 512 bits, bit-error rate t/n \= 0.15 (15\\% noise), and k\_{\\text{sub}} \= 32 bits per subset, p\_{\\text{clean}} \\approx (0.85)^{32} \\approx 0.0055. With \\ell \= 1500 lockers, \\delta\_{\\text{FRR}} \\le e^{-8.28} \\approx 0.00025 (0.025\\%), and verification takes \< 1.5\\text{ ms} in C/Rust using hardware SHA/AES instructions while maintaining computational reusability across multiple updates.

#### **Architecture C: Cancelable Biometrics via Salted BioHashing & Adaptive Bloom Filters**

When an application requires **stateless similarity scoring without recovering the raw vector in RAM during verification**, ZTBE provides an ISO/IEC 24745 cancelable transformation based on Rathgeb et al. (2014):

> 1. **Salted Orthogonal Projection (BioHashing):** Given application/user key K\_{\\text{app}}, generate a pseudo-random orthonormal matrix \\mathbf{Q}\_{K} \\in \\mathbb{R}^{n \\times D} and project \\tilde{\\mathbf{z}}: b\_i \= \\mathbb{I}\\left( (\\mathbf{Q}\_K \\tilde{\\mathbf{z}})\_i \\ge 0 \\right) \\in \\{0, 1\\}  
> 2. **Irreversible Many-to-One Bloom Filter Mapping:** Partition the binary matrix into B blocks, each containing N\_b columns of length W\_b bits. For each block r \\in \\{1, \\dots, B\\}, initialize a Bloom filter \\mathbf{BF}\_r \\in \\{0, 1\\}^{2^{W\_b}} of zeros. For each column vector \\mathbf{c}\_{r,j} \\in \\{0, 1\\}^{W\_b} (j \\in \\{1, \\dots, N\_b\\}), compute its integer value \\text{int}(\\mathbf{c}\_{r,j}) \\in \[0, 2^{W\_b}-1\] and set the corresponding bit: \\mathbf{BF}\_r\\left\[\\text{int}(\\mathbf{c}\_{r,j})\\right\] \= 1  
> 3. **Why It Is Irreversible:** Because N\_b \> 2^{W\_b} or multiple distinct columns map to the same index (collisions) and column ordering is destroyed within each block, inverting \\mathbf{BF}\_r to recover the original bit locations has an exponential number of pre-images: N\_{\\text{pre-images}} \= \\prod\_{r=1}^{B} \\sum\_{k=0}^{|\\mathbf{BF}\_r|} (-1)^k \\binom{|\\mathbf{BF}\_r|}{k} \\left(|\\mathbf{BF}\_r| \- k\\right)^{N\_b}  
> 4. **Fast Verification in Compressed Space:** Verification compares a fresh Bloom filter template \\mathbf{BF}' directly against the stored \\mathbf{BF} using bitwise AND and popcount instructions (\_\_builtin\_popcountll), without ever reconstructing the original behavioral vector: D\_{\\text{BF}}(\\mathbf{BF}, \\mathbf{BF}') \= \\frac{1}{B} \\sum\_{r=1}^{B} \\frac{\\text{wt}(\\mathbf{BF}\_r \\oplus \\mathbf{BF}'\_r)}{\\text{wt}(\\mathbf{BF}\_r) \+ \\text{wt}(\\mathbf{BF}'\_r)}

## **5\. Mathematical Approaches for (Semi-)Continuous Profile Adjustment**

The defining requirement of ZTBE is **continuous or semi-continuous adjustment** of an irreversible profile. Because a cryptographic hash or secure sketch cannot be inverted by the server alone to inspect the user's underlying feature distribution, updating the template requires specialized protocols. Below are the three mathematical mechanisms researched and specified for ZTBE.

### **5.1 Approach 1: Authenticated Ephemeral Decoupling (Verify-Adapt-Rehash Loop)**

**Applicable to:** Architecture A (Syndrome Fuzzy Extractor) & Architecture B (Sample-then-Lock Reusable Fuzzy Extractor).  
While the stored profile \\mathcal{T}^{(t)} is irreversible *at rest*, a successful verification \\text{Rep}(w', \\mathcal{T}^{(t)}) momentarily witnesses the legitimate user's current behavior w' (and in Architecture A, recovers the previous reference w^{(t)} \= w' \\oplus \\hat{e}) in ephemeral RAM.  
\[Incoming Telemetry Window\] \---\> \[Quantize to w'\]  
                                       |  
                                       v  
\[Stored Irreversible Profile T^(t)\] \-\> \[Rep(w', T^(t))\] \---\> (Fails) \-\> Reject & Discard w'  
                                       |  
                                  (Succeeds: d\_H \<= t\_adapt)  
                                       |  
                                       v  
                         \[Ephemeral Bit-Level Drift Blending\]  
                         \[w^(t+1) \= MajorityVote / BernoulliEMA(w^(t), w')\]  
                                       |  
                                       v  
                         \[Gen(w^(t+1)) \-\> New Profile T^(t+1)\]  
                                       |  
                                       v  
                         \[Overwrite T^(t) & Zero RAM (explicit\_bzero)\]

#### **Mathematical Formulation of Binary Drift Blending:**

When w^{(t)} \\in \\{0, 1\\}^n is recovered in ephemeral memory via \\hat{w}^{(t)} \= w' \\oplus \\text{Decode}\_{\\mathcal{C}}(\\mathbf{H}\_{\\mathcal{C}}(w')^T \\oplus P\_{\\text{syn}}^{(t)}), how do we blend binary strings w^{(t)} and w' with learning rate \\eta \\in (0, 1)?

> 1. **Gray-Decoded Continuous Interpolation (Preferred):** Since w^{(t)} is composed of D Gray-coded m-bit blocks, decode each m-bit block of w^{(t)} back to its quantized integer bin q\_j^{(t)} \= \\mathcal{G}^{-1}(w\_j^{(t)}) \\in \\{0, \\dots, 2^m \- 1\\} and blend with the newly observed continuous standardized feature \\tilde{z}'\_j: \\hat{z}\_j^{(t+1)} \= (1 \- \\eta) \\Phi^{-1}\\left(\\frac{q\_j^{(t)} \+ 0.5}{2^m}\\right) \+ \\eta \\tilde{z}'\_j Then re-quantize \\hat{z}\_j^{(t+1)} via Gray coding into w^{(t+1)} \\in \\{0, 1\\}^n.  
> 2. **Probabilistic Bit-Flipping (For Pure Binary Sample-then-Lock):** When only w' is known (as in Architecture B where \\text{Rep} recovers R directly without decoding w^{(t)}), the engine accumulates K\_{\\text{epoch}} verified windows w'^{(1)}, \\dots, w'^{(K\_{\\text{epoch}})} in a short-lived ephemeral counter array \\mathbf{c}\_{\\text{bit}} \\in \\mathbb{Z}\_{\\ge 0}^n (requiring only 512\\text{ bytes} of RAM during an active session). At the end of the session or epoch, the updated template vector is computed via thresholded majority voting: w\_i^{(t+1)} \= \\mathbb{I}\\left( \\frac{1}{K\_{\\text{epoch}}} \\sum\_{m=1}^{K\_{\\text{epoch}}} w'^{(m)}\_i \\ge 0.5 \\right) Then \\text{Gen}(w^{(t+1)}) \\rightarrow \\mathcal{T}^{(t+1)} is executed to generate fresh digital lockers with independent nonces and subsets, ensuring **reusability security** even if an adversary observes the sequence of database updates \\mathcal{T}^{(1)}, \\mathcal{T}^{(2)}, \\dots, \\mathcal{T}^{(k)}.

### **5.2 Approach 2: Syndrome-Space Homomorphic Drift Shifting (Zero-Recovery Update)**

**Applicable to:** Architecture A (Linear Code Syndrome Sketches).  
Because the parity-check matrix \\mathbf{H}\_{\\mathcal{C}} is a **linear operator over \\mathbb{F}\_2**, the stored helper syndrome P\_{\\text{syn}}^{(t)} \= \\mathbf{H}\_{\\mathcal{C}} \\left(w^{(t)}\\right)^T exhibits additive homomorphism over \\mathbb{F}\_2^n:

\\mathbf{H}\_{\\mathcal{C}} \\left(w^{(t)} \\oplus \\Delta w\\right)^T \= \\mathbf{H}\_{\\mathcal{C}} \\left(w^{(t)}\\right)^T \\oplus \\mathbf{H}\_{\\mathcal{C}} (\\Delta w)^T \= P\_{\\text{syn}}^{(t)} \\oplus \\mathbf{H}\_{\\mathcal{C}} (\\Delta w)^T

#### **How It Works:**

> 1. During verification of w', the syndrome decoder finds the exact error vector \\hat{e} \= w^{(t)} \\oplus w' with \\text{wt}(\\hat{e}) \\le t.  
> 2. Suppose we wish to adapt the profile partially toward w' by correcting only systematic/persistent drift bits while ignoring random noise. We construct a sparse drift vector \\Delta w \\in \\{0, 1\\}^n by selecting a random or confidence-weighted fraction \\eta \\in (0, 1\) of the set bits in \\hat{e} (so \\text{wt}(\\Delta w) \= \\lfloor \\eta \\cdot \\text{wt}(\\hat{e}) \\rfloor).  
> 3. The syndrome can be updated **in place** via: P\_{\\text{syn}}^{(t+1)} \= P\_{\\text{syn}}^{(t)} \\oplus \\mathbf{H}\_{\\mathcal{C}} (\\Delta w)^T \\oplus \\mathbf{H}\_{\\mathcal{C}} (c\_{\\text{re-blind}})^T \= P\_{\\text{syn}}^{(t)} \\oplus \\mathbf{H}\_{\\mathcal{C}} (\\Delta w)^T *(since \\mathbf{H}\_{\\mathcal{C}} c^T \= \\mathbf{0} for any codeword c \\in \\mathcal{C})*.

**Critical Security Caveat (Helper Data Difference Leakage):** If an attacker monitors the database before and after an update, they can compute:  
P\_{\\text{syn}}^{(t+1)} \\oplus P\_{\\text{syn}}^{(t)} \= \\mathbf{H}\_{\\mathcal{C}} (\\Delta w)^T  
Because \\Delta w is sparse (\\text{wt}(\\Delta w) \\le t), the attacker can run \\text{Decode}\_{\\mathcal{C}}(P\_{\\text{syn}}^{(t+1)} \\oplus P\_{\\text{syn}}^{(t)}) to learn the exact bit positions \\Delta w that drifted\! Over many updates, accumulating \\sum \\Delta w^{(k)} narrows down the search space of w. *Mitigation:* Whenever updating the syndrome, the system **must also apply a secret-keyed column permutation** \\pi\_{K^{(t+1)}} or switch to a fresh generator/parity matrix \\mathbf{H}\_{\\mathcal{C}}^{(t+1)}, which breaks linear correlation across epochs.

### **5.3 Approach 3: Time-Decaying Counting Bloom Filters (Continuous In-Place Cancelable Adaptation)**

**Applicable to:** Architecture C (Cancelable Bloom Filter Templates).  
To allow truly continuous, event-by-event profile adjustment without ever reconstructing the feature vector or storing raw session accumulators:

> 1. Replace each binary Bloom filter bit \\mathbf{BF}\_r\[idx\] \\in \\{0, 1\\} with a bounded **4-bit saturating counter** \\mathbf{CBF}\_r\[idx\] \\in \\{0, 1, \\dots, 15\\}. (A template of B \= 32 blocks with 2^{W\_b} \= 256 slots uses only 32 \\times 256 \\times 0.5\\text{ bytes} \= 4\\text{ KB}).  
> 2. **Verification:** The active binary Bloom filter \\mathbf{BF}\_r is derived dynamically by thresholding the counters at \\tau\_{\\text{active}} \= 4: \\mathbf{BF}\_r\[idx\] \= \\mathbb{I}\\left(\\mathbf{CBF}\_r\[idx\] \\ge \\tau\_{\\text{active}}\\right)  
> 3. **Continuous Update Step:** When a fresh behavioral window \\mathbf{BF}' is verified with high confidence (D\_{\\text{BF}}(\\mathbf{BF}, \\mathbf{BF}') \\le \\theta\_{\\text{adapt}}):  
   * **Exponential Decay (Forgetting Old Habits):** Every M\_{\\text{decay}} updates, decrement all non-zero counters by 1 (or multiply by (1 \- \\lambda\_{\\text{decay}})): \\mathbf{CBF}\_r\[idx\] \\leftarrow \\max\\left(0, \\; \\mathbf{CBF}\_r\[idx\] \- 1\\right)  
   * **Habit Reinforcement:** For every active bit \\mathbf{BF}'\_r\[idx\] \= 1 in the newly verified window: \\mathbf{CBF}\_r\[idx\] \\leftarrow \\min\\left(15, \\; \\mathbf{CBF}\_r\[idx\] \+ \\Delta\_{\\text{inc}}\\right)  
> 4. **Why Irreversibility Holds:** Because the many-to-one block projection occurs *before* the counters are incremented, each counter slot idx \\in \\{0, \\dots, 2^{W\_b}-1\\} aggregates collisions from N\_b distinct BioHashed feature columns. Even with 4-bit counter granularity, recovering the pre-image requires inverting both the non-injective column-block mapping and the salted random projection \\mathbf{Q}\_K.

### **5.4 Comparison Matrix of Continuous Adjustment Approaches**

| Criterion | Approach 1: Sample-then-Lock RFE Loop | Approach 2: Syndrome-Space Shifting | Approach 3: Decaying Counting Bloom Filter |
| :---- | :---- | :---- | :---- |
| **Cryptographic Primitive** | Digital Lockers (HKDF / AES-GCM) | Error-Correcting Codes (BCH / Polar) | Salted Orthogonal Projection \+ Bloom Filter |
| **Security Model** | Computational (Standard / RO Model) | Information-Theoretic (Single Enrollment) | Cancelable / Unlinkable (Requires Secret Salt K) |
| **Resistant to Multi-Update Correlation?** | **Yes** (Provably reusable under correlated drift) | **No** (Unless matrix \\mathbf{H}\_{\\mathcal{C}} is rotated per update) | **Partial** (Requires periodic salt rotation if DB is watched) |
| **Derives Exact Cryptographic Key R?** | **Yes** (256-bit uniform key) | **Yes** (128–256-bit key) | **No** (Outputs similarity distance score only) |
| **Update Granularity** | Semi-Continuous (Session / Epoch boundary) | Semi-Continuous (Per window) | **Truly Continuous** (In-place per window) |
| **Profile Storage Size** | 24\\text{ KB} \- 48\\text{ KB} (\\ell \\approx 1000 lockers) | \\mathbf{128\\text{ Bytes}} (Ultra-compact syndrome) | \\mathbf{2\\text{ KB} \- 4\\text{ KB}} (4-bit counter array) |
| **Verification Latency** | 1.0\\text{ ms} \- 3.5\\text{ ms} | 0.4\\text{ ms} \- 1.2\\text{ ms} | \< \\mathbf{0.1\\text{ ms}} (Bitwise POPCNT) |

**Recommended Hybrid Architecture for ZTBE:** ZTBE combines **Approach 3 (Decaying Counting Bloom Filter)** as the **Fast Continuous L1 Filter** (evaluating every 10\\text{ seconds} in \< 0.1\\text{ ms}) with **Approach 1 (Sample-then-Lock Reusable Fuzzy Extractor)** as the **L2 Cryptographic Key Anchor** (evaluated at session start and re-keyed at session end).

## **6\. Anti-Poisoning & Adversarial Drift Control**

A critical vulnerability of any self-updating biometric system is a **Boiling-Frog / Adversarial Drift Attack** (also known as a template poisoning attack). If an attacker gains access to an unlocked terminal or injects synthetic telemetry that lies *just inside* the verification threshold (d\_H(w^{(t)}, w\_{\\text{adv}}) \= t \- 1), an unprotected adaptive loop will shift w^{(t+1)} toward w\_{\\text{adv}}, eventually locking out the legitimate user and enrolling the attacker.  
ZTBE enforces three mathematical safeguards before permitting any profile adaptation:

### **6.1 Dual-Threshold Hysteresis Gate (t\_{\\text{adapt}} \< t\_{\\text{verify}})**

Define two strictly separated Hamming distance thresholds:

> * **Verification Threshold (t\_{\\text{verify}}):** Maximum error tolerated to pass authentication (e.g., t\_{\\text{verify}} \= 0.18 n).  
> * **Adaptation Threshold (t\_{\\text{adapt}}):** Maximum error tolerated to trigger profile adaptation, constrained by: t\_{\\text{adapt}} \= \\gamma\_{\\text{gate}} \\cdot t\_{\\text{verify}}, \\quad \\gamma\_{\\text{gate}} \\in \[0.45, 0.65\]

Any behavioral window w' with t\_{\\text{adapt}} \< d\_H(w^{(t)}, w') \\le t\_{\\text{verify}} is **authenticated** (e.g., user is typing one-handed while holding a coffee cup), but **excluded from updating the profile**.

### **6.2 Drift Velocity Clamping**

Even when d\_H(w^{(t)}, w') \\le t\_{\\text{adapt}}, the maximum Hamming shift allowed over any rolling 24-hour window is bounded by V\_{\\max} (e.g., V\_{\\max} \= 0.02 n bits/day):

d\_H\\left(w^{(\\text{day\\\_start})}, w^{(t+1)}\\right) \\le V\_{\\max}

### **6.3 Anchor Template Divergence Bound**

Upon initial verified enrollment, a separate long-term **Anchor Fuzzy Extractor** \\mathcal{T}\_{\\text{anchor}} is stored with a wider error tolerance t\_{\\text{anchor}} \= 1.35 t\_{\\text{verify}}. Even as the working profile \\mathcal{T}^{(t)} adapts over months, any update must continue to satisfy \\text{Rep}(w', \\mathcal{T}\_{\\text{anchor}}) \= \\text{VALID} unless an explicit multi-factor re-enrollment occurs.

## **7\. System Architecture & Reference FOSS Stack**

### **7.1 High-Level Pipeline Architecture**

\+-----------------------------------------------------------------------------------+  
| CLIENT / EDGE EPHEMERAL ZONE (Protected RAM \- mlock() / Zero Disk Swap)           |  
|                                                                                   |  
|  \+-----------------------+    \+-------------------------+    \+-----------------+  |  
|  | Interaction Collectors|    | Online Stream Profiler  |    | Gray Quantizer  |  |  
|  | \- Flagon UserALE.js   |---\>| \- River (EWMean/EWVar)  |---\>| & Reliability   |  |  
|  | \- OS Input Hooks      |    | \- Markov Transition Est.|    | Mask (w' in F\_2)|  |  
|  \+-----------------------+    \+-------------------------+    \+--------+--------+  |  
|                                                                       |           |  
|                                                                       v           |  
|  \+-----------------------------------------------------------------------------+  |  
|  | Cryptographic BTP Engine                                                    |  |  
|  | \- L1 Fast Filter: Salted BioHash \+ Counting Bloom Filter (POPCNT)           |  |  
|  | \- L2 Key Anchor : Sample-then-Lock RFE / BCH Syndrome Fuzzy Extractor       |  |  
|  | \- Drift Gate    : Dual-Threshold (t\_adapt \< t\_verify) \+ explicit\_bzero()    |  |  
|  \+--------------------------------------+--------------------------------------+  |  
\+-----------------------------------------|-----------------------------------------+  
                                          |  
                     Only Irreversible Templates Cross Boundary  
                     T \= (P\_helper, SHA256(R), CBF\_counters)  
                                          |  
                                          v  
\+-----------------------------------------------------------------------------------+  
| PERSISTENT STORAGE ZONE (Database / Untrusted Storage)                            |  
|                                                                                   |  
|  \+-----------------------------------------------------------------------------+  |  
|  | User Record: { user\_id, epoch\_id, P\_helper, H(R), CBF\_4bit\_state }          |  |  
|  | Guarantee  : H\_inf(W | T) \>= 80 bits (Cannot reconstruct habits from DB)    |  |  
|  \+-----------------------------------------------------------------------------+  |  
\+-----------------------------------------------------------------------------------+

### **7.2 Recommended FOSS Component Mapping**

| Subsystem | FOSS Library / Project | License | Role in ZTBE |
| :---- | :---- | :---- | :---- |
| **Web Telemetry Capture** | **Apache Flagon (UserALE.js)** | Apache-2.0 | Captures DOM clicks, mouse trajectories, scroll cadence, and navigation transitions with a \< 15\\text{ KB} footprint. |
| **OS Keystroke / Mouse Capture** | **rdev (Rust)** or **pynput / evdev** | MIT / BSD | Low-overhead cross-platform kernel/window-system hooks for key press/release and pointer events. |
| **Streaming Online ML** | **River (online-ml/river)** or custom Rust EWMA struct | BSD-3-Clause | Computes single-pass O(1) running means (stats.EWMean), variances (stats.EWVar), and streaming quantiles (stats.Quantile). |
| **Fuzzy Extractor (Sample-then-Lock)** | **python-fuzzy-extractor** / **whyamey/feap (C/Rust)** | MIT / GPL-3.0 | Implements digital-locker reusable fuzzy extractors (Gen and Rep) over Hamming space. |
| **Syndrome Error Correction** | **bchlib** or **reedsolo / ezpwd-reed-solomon** | MIT / LGPL | Fast C/C++ finite-field syndrome computation \\mathbf{H}\_{\\mathcal{C}} w^T and Berlekamp-Massey bounded-distance decoding. |
| **Cancelable Bloom Filter BTP** | **dasec/face-bf-btp** (adapted for behavioral vectors) | Open Source | Implements ISO/IEC 24745 irreversible column-block Bloom filter transformations and unlinkability evaluation. |
| **Secure Memory Management** | **zeroize (Rust)** / libsodium sodium\_mlock | Apache-2.0 / ISC | Locks ephemeral behavioral buffers in physical RAM (preventing OS swap leakage) and guarantees compiler-safe memory wiping. |

## **8\. Open Questions & Further Considerations**

The following architectural and mathematical questions require product-level decisions and empirical validation prior to production deployment:

### **8.1 Feature Engineering & Modality Availability**

> 1. **Missing Modality Handling (Erasure Coding):** In practice, a user may browse for 5\\text{ minutes} using only the mouse/trackpad without typing a single key, or code in an IDE using only the keyboard without touching the mouse.  
   * *Open Question:* Should ZTBE maintain **separate modular profiles per modality** (\\mathcal{T}\_{\\text{key}}, \\mathcal{T}\_{\\text{mouse}}, \\mathcal{T}\_{\\text{nav}}) or use an **erasure-capable Fuzzy Extractor** that treats missing modalities as known erasures (which consume half the error-correcting capacity of random bit flips: 2 t\_{\\text{errors}} \+ e\_{\\text{erasures}} \< d\_{\\min})?  
> 2. **Hardware & Peripheral Switching:** A user switching from an integrated laptop trackpad to an external high-DPI gaming mouse, or from a membrane keyboard to a mechanical keyboard, exhibits an immediate step-change in dwell time and pointer jerk.  
   * *Open Question:* Should the profile key be salted with a **hardware peripheral fingerprint** (e.g., USB HID class or screen resolution category) so each user automatically maintains up to k device-contextual profiles?

### **8.2 Cryptographic & Information-Theoretic Bounds**

> 1. **True Min-Entropy of Behavioral Biometrics (H\_\\infty(W)):** Academic studies on keystroke and mouse dynamics (e.g., Ballard et al., Monroe et al.) suggest that behavioral biometrics possess significantly lower intrinsic min-entropy (20 to 45\\text{ bits} of true inter-subject entropy) than iris or fingerprint biometrics (\> 100\\text{ bits}).  
   * *Open Question:* If H\_\\infty(W) \\approx 35\\text{ bits}, an offline attacker who steals the database \\mathcal{T} \= (P, H(R)) cannot invert \\mathcal{T} algebraically, but *could* run an offline dictionary attack by simulating synthetic behavioral vectors drawn from a population prior \\mathcal{D}\_{\\text{pop}} and testing \\text{Rep}(w\_{\\text{sim}}, P). Should \\text{Rep} incorporate a **memory-hard key derivation step** (e.g., \\text{Argon2id} inside the locker or syndrome key extraction) to make offline population-dictionary attacks computationally prohibitive while keeping single-user verification under 20\\text{ ms}?  
> 2. **Custody of the Application Salt (K\_{\\text{app}}) in Architecture C:**  
   * *Open Question:* In Cancelable Bloom Filters, if the projection seed K\_{\\text{app}} is stored in the same database as the Bloom filter \\mathbf{BF}, an attacker who dumps the entire server only faces the many-to-one Bloom filter pre-image barrier, not the orthogonal projection barrier. Will K\_{\\text{app}} be held on the client device, inside a Hardware Security Module (HSM)/TPM, or derived from a user token?

### **8.3 Adaptation Dynamics & Cold-Start UX**

> 1. **Cold-Start Enrollment Horizon:** How many interactions are required before the initial profile \\mathcal{T}^{(0)} stabilizes enough to lock the quantization intervals and reliability mask M\_{\\text{rel}}?  
   * *Open Question:* During the first N\_{\\text{cold}} interactions (e.g., first 500 keystrokes and 200 mouse movements), where is the provisional variance stored before \\mathcal{T}^{(0)} is minted? Can it be held in client-side encrypted IndexedDB / OS Keychain until enrollment completes?  
> 2. **Abrupt Legitimate Changes (Injury / Accessibility):** If a user breaks a finger or changes accessibility settings, their behavior will exceed t\_{\\text{verify}}.  
   * *Open Question:* What is the fallback re-enrollment trigger, and should the old profile be completely revoked or archived as a temporary recovery state?

## **9\. References & Standards**

### **9.1 International Standards**

> 1. **ISO/IEC 24745:2022:** *Information security, cybersecurity and privacy protection — Biometric information protection*. Defines the formal requirements for **Irreversibility**, **Unlinkability**, **Renewability**, and **Confidentiality** of protected biometric references (Pseudonymous Identifiers PI and Auxiliary Data AD).  
> 2. **ISO/IEC 30136:2018:** *Information technology — Biometrics — Performance testing of biometric template protection schemes*. Specifies metrics for evaluating privacy leakage, diversity, and verification accuracy trade-offs.

### **9.2 Cryptographic & Biometric Template Protection Literature**

> 1. **Dodis, Y., Ostrovsky, R., Reyzin, L., & Smith, A. (2008).** "Fuzzy Extractors: How to Generate Strong Keys from Biometrics and Other Noisy Data." *SIAM Journal on Computing*, 38(1), 97–139. (Foundational definition of Secure Sketches \\text{SS} and Fuzzy Extractors (\\text{Gen}, \\text{Rep})).  
> 2. **Canetti, R., Fuller, B., Paneth, O., Reyzin, L., & Smith, A. (2016/2021).** "Reusable Fuzzy Extractors for Low-Entropy Distributions." *Journal of Cryptology*, 34(1), 1–46 / *EUROCRYPT 2016*. (Introduces the Sample-then-Lock construction enabling reusable fuzzy extraction across correlated noisy readings and low-entropy-rate sources).  
> 3. **Boyen, X. (2004).** "Reusable Cryptographic Fuzzy Extractors." *Proceedings of the 11th ACM Conference on Computer and Communications Security (CCS)*, 82–91. (Proves that naive code-offset fuzzy extractors leak secrets when re-enrolled multiple times on correlated shifts of the same biometric).  
> 4. **Juels, A., & Wattenberg, M. (1999).** "A Fuzzy Commitment Scheme." *Proceedings of the 6th ACM Conference on Computer and Communications Security (CCS)*, 28–36. (Introduces error-correcting code-offset commitments P \= w \\oplus c).  
> 5. **Rathgeb, C., Breitinger, F., & Busch, C. (2014).** "Alignment-Free Cancelable Iris Biometric Templates Based on Adaptive Bloom Filters." *IEEE International Conference on Biometrics (ICB)* / *IET Biometrics*. (Defines the irreversible column-block to Bloom filter cancelable transformation).  
> 6. **Teoh, A. B. J., Ngo, D. C. L., & Goh, A. (2004).** "BioHashing: Two factor authentication featuring fingerprint data and tokenised random number." *Pattern Recognition*, 37(11), 2245–2255. (Introduces random orthonormal projection and quantization for cancelable biometrics).  
> 7. **Gomez-Barrero, M., Galbally, J., Rathgeb, C., & Busch, C. (2017).** "General Framework to Evaluate Unlinkability in Biometric Template Protection Systems." *IEEE Transactions on Information Forensics and Security*, 13(6), 1406–1420.

### **9.3 Behavioral Biometrics, Quantization & Poisoning Attacks**

> 1. **Monrose, F., Reiter, M. K., & Wetzel, S. (2002).** "Password Hardening Based on Keystroke Dynamics." *International Journal of Information Security*, 1(2), 69–83. (Early cryptographic key hardening from keystroke latency quantization).  
> 2. **Ballard, L., Lopresti, D., & Monrose, F. (2007).** "Forgery Quality and its Implications for Behavioral Biometric Security." *IEEE Transactions on Systems, Man, and Cybernetics*, 37(5), 1107–1118. (Analyzes empirical entropy limits of behavioral biometrics).  
> 3. **Biggio, B., Fumera, G., Roli, F., & Didaci, L. (2012).** "Poisoning Adaptive Biometric Systems." *Structural, Syntactic, and Statistical Pattern Recognition (SSPR/SPR)*, LNCS 7626, 417–425. (Mathematical analysis of adversarial drift/poisoning attacks against self-updating biometric templates and dual-threshold defenses).

### **9.4 Open-Source Software & Reference Implementations**

> 1. **Apache Flagon (UserALE.js & Distill):** [https\://flagon.apache.org/](https://flagon.apache.org/) — Behavioral logging and telemetry segmentation framework.  
> 2. **River (online-ml/river):** [https\://github.com/online-ml/river](https://github.com/online-ml/river) — Streaming machine learning and O(1) statistical tracking in Python.  
> 3. **python-fuzzy-extractor:** [https\://github.com/carter-yagemann/python-fuzzy-extractor](https://github.com/carter-yagemann/python-fuzzy-extractor) — Digital-locker fuzzy extractor implementation.  
> 4. **feap (whyamey/feap):** [https\://github.com/whyamey/feap](https://github.com/whyamey/feap) — C and Rust implementation of Sample-then-Lock reusable fuzzy extractors.  
> 5. **da/sec Biometric Template Protection (dasec/face-bf-btp):** [https\://github.com/dasec/face-bf-btp](https://github.com/dasec/face-bf-btp) — Reference implementation of ISO/IEC 24745 Bloom filter template protection.