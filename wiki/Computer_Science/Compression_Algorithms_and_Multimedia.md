---
tags: [computer_science, archiving, algorithms, multimedia, compression]
date_created: 2026-04-12
sources:
  - "[[Akitando 70 - Entendendo GIT  (não é um tutorial!)]] (Clipper)"
  - "[[Akitando 116 - De 5 Tera a 25 Giga  Compressão de Dados e Multimídia]] (Clipper)"
---
# Compression Algorithms and Multimedia

The history of file storage is a constant battle against physical disk limitations and bandwidth. Modern multimedia and archival formats are built upon mathematical compression algorithms that balance data fidelity with storage efficiency.

## Lossless vs. Lossy

| Feature | Lossless Compression | Lossy Compression |
| :--- | :--- | :--- |
| **Integrity** | Bit-perfect restoration (Data = Original) | Data is discarded (Data &approx; Original) |
| **Efficiency** | Lower compression ratios | Extremely high compression ratios |
| **Use Cases** | Databases, Executables, Text archives | Images (JPEG), Video (H.264), Audio (MP3) |
| **Algorithms** | Huffman, LZ77, LZW | DCT, Quantization, Subsampling |

## Lossless Foundations

### Huffman Coding (Entropy Encoding)
A fundamental entropy-based algorithm that assigns shorter binary codes to more frequent characters and longer codes to rarer ones. This creates a "perfect" variable-length code where no code is a prefix of another (Prefix-free code).

### Lempel-Ziv (Dictionary-based)
Algorithms like **LZ77** and **LZW** (Lempel-Ziv-Welch) find repeating patterns in a data stream and replace subsequent occurrences with a pointer (distance/length) to the first occurrence.
- **Deflate**: The core of Gzip/ZIP, combining LZ77 for redundancy reduction and Huffman for entropy encoding.

## Lossy Multimedia Compression

Multimedia utilizes the limitations of human perception (Psychovisuals and Psychoacoustics) to discard "unnoticeable" data.

### 1. Chroma Subsampling (YUV)
Human vision is more sensitive to luminance (brightness) than chrominance (color).
- **YUV Model**: Separates Luminance (**Y**) from Blue-difference (**U**) and Red-difference (**V**).
- **4:2:2 or 4:2:0**: Color resolution is reduced by half or three-quarters, significantly decreasing bandwidth while the human eye barely notices the difference.

### 2. Discrete Cosine Transform (DCT)
The foundation of JPEG and MPEG.
- **Frequency Domain**: DCT converts 8x8 blocks of pixels from the spatial domain into the frequency domain. 
- **Low-pass filtering**: High-frequency components (sharp details/noise) are separated from low-frequency components (general shapes/colors).

### 3. Quantization
The "lossy" step where high-frequency coefficients from the DCT are divided by factors (from a quantization table) and rounded to the nearest integer. This results in many zeros, which are easily compressed via **Run-Length Encoding (RLE)**.

## Video Compression (Temporal Redundancy)

Video compresses data by not storing every frame as a full image, but rather the differences between them.

### Frame Types
- **I-Frames (Intra-coded)**: Full independent images (like a JPEG). The only points where you can "seek" instantly.
- **P-Frames (Predicted)**: Delta frames that store only the changes from the previous frame using motion vectors.
- **B-Frames (Bi-predictive)**: Advanced deltas that look both forward and backward in time for redundancy.

### Professional vs. Delivery Codecs
- **Delivery (H.264/HEVC)**: High inter-frame compression. Efficient for streaming but hard on CPU/GPU during editing due to frame dependencies.
- **Professional (ProRes, DNxHR)**: Primarily Intra-frame (all frames are I-frames). Large file sizes (500Mbps+) but extremely fast to decode during Non-Linear Editing (NLE).
