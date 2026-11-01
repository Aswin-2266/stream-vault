# stream-vault

> A lightweight hybrid media indexing, cloud relay, and HTTP streaming engine.

---

## ⚡ Overview

**stream-vault** is a private, self-hosted media router that bridges Telegram cloud storage and direct HTTP range streaming. It eliminates third-party token expirations and ad-gateways by maintaining an isolated, indexed cloud vault.

### Key Capabilities
- **Hybrid Sourcing:** Automatically indexes media from public channels and falls back to an automated cloud engine when an item is not found.
- **Direct Stream Delivery (DDL):** Exposes an embedded asynchronous HTTP web server handling byte-range requests for instantaneous playback in VLC, MPV, or web browsers.
- **Lossless Stream Splitting:** Automatically slices media files exceeding 2 GB into seamless parts using `ffmpeg` stream copying without re-encoding.
- **Zero-Trust Access Control:** Strictly whitelisted authorization ensuring only verified accounts can interact with or trigger tasks.

---

## 🚀 Quick Start

1. **Prerequisites & Credentials:**
   Follow our detailed [Credentials Setup Guide](docs/setup-guide.md) to set up your Telegram Bot Token, MTProto API keys, and free MongoDB Atlas cluster.

2. **System Architecture:**
   Review the detailed architectural specifications in [Architecture Plan](docs/architecture-plan.md).

---

## 📄 License

MIT License. Designed for personal archiving, backup, and private streaming workflows.
