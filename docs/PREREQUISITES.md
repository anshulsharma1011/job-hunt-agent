# Prerequisites — Job Hunt Agent

This guide walks you through everything you need to install before running the Job Hunt Agent.
Written for a **fresh macOS machine**. No prior developer experience assumed.

---

## System Requirements

Before you begin, make sure your machine meets these minimums:

| Requirement | Minimum | Recommended |
|------------|---------|-------------|
| macOS version | Monterey 12.0+ | Ventura 13+ or Sonoma 14+ |
| RAM | 8 GB | 16 GB |
| Free disk space | 20 GB | 30 GB |
| Chip | Intel or Apple Silicon | Apple Silicon (M1/M2/M3/M4) |

> **Why so much RAM?** The local AI model (`llama3.1:8b`) loads entirely into memory. 8 GB is the floor — 16 GB gives it room to run comfortably alongside your other apps.

To check your macOS version: Apple menu () → **About This Mac**.

---

## What You Will Install

| Tool | What it is | Why we need it |
|------|-----------|----------------|
| Homebrew | Package manager for macOS | Installs everything else cleanly |
| Python 3.12 | Programming language | The agent is written in Python |
| Git | Version control | Download and update the project code |
| MongoDB | Local database | Stores jobs, your profile, cycle history |
| Ollama | Local AI model runner | Runs the AI model on your machine |
| llama3.1:8b | AI language model | Powers job scoring and profile parsing |

---

## Step 1 — Homebrew

Homebrew is a tool that installs software on macOS from the command line. Think of it as an App Store for developer tools.

**Open Terminal:**
- Press `Cmd + Space`, type `Terminal`, press `Enter`

**Install Homebrew:**
```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

You will be asked for your Mac login password. Type it (nothing will appear on screen — that is normal) and press `Enter`.

The install takes 5–10 minutes.

**After install, follow the "Next steps" printed in the terminal.** It will ask you to run 2 commands to add Homebrew to your PATH. Run both.

**Verify:**
```bash
brew --version
```
Expected output: `Homebrew 4.x.x`

**Reference:** https://brew.sh

---

## Step 2 — Git

Git is used to download the project code and keep it up to date.

```bash
brew install git
```

**Verify:**
```bash
git --version
```
Expected output: `git version 2.x.x`

**Reference:** https://git-scm.com/doc

---

## Step 3 — Python 3.12

The agent is written in Python. We install a specific version to avoid compatibility issues.

```bash
brew install python@3.12
```

After install, link it so your terminal uses this version by default:
```bash
brew link python@3.12
```

**Verify:**
```bash
python3.12 --version
```
Expected output: `Python 3.12.x`

Also verify pip (Python's package installer) is available:
```bash
pip3.12 --version
```
Expected output: `pip 24.x.x from ...`

**Reference:** https://docs.python.org/3.12

---

## Step 4 — MongoDB

MongoDB is the local database where the agent stores everything — job opportunities, your profile, scoring history, cycle reports.

**Install MongoDB:**
```bash
brew tap mongodb/brew
brew install mongodb-community
```

**Start MongoDB (runs in background, auto-starts on login):**
```bash
brew services start mongodb-community
```

**Verify MongoDB is running:**
```bash
brew services list | grep mongodb
```
Expected output: `mongodb-community started ...`

You can also check it responds:
```bash
mongosh --eval "db.runCommand({ connectionStatus: 1 })" --quiet
```
Expected output: `{ ok: 1 }`

**Stop MongoDB (if you ever need to):**
```bash
brew services stop mongodb-community
```

**Reference:** https://www.mongodb.com/docs/manual/tutorial/install-mongodb-on-os-x

---

## Step 5 — Ollama

Ollama lets you run AI language models locally on your Mac. It handles all the complexity of loading and running the model.

**Install Ollama:**
```bash
brew install ollama
```

**Start Ollama (runs in background):**
```bash
brew services start ollama
```

**Verify Ollama is running:**
```bash
curl http://localhost:11434/
```
Expected output: `Ollama is running`

**Reference:** https://ollama.com/download

---

## Step 6 — Download the AI Model

This downloads the `llama3.1:8b` model that the agent uses to score jobs and parse your resume. It is approximately **5 GB** — make sure you are on a stable internet connection before running this.

```bash
ollama pull llama3.1:8b
```

This will take 10–20 minutes depending on your connection. You will see a progress bar.

**Verify the model downloaded:**
```bash
ollama list
```
Expected output:
```
NAME           ID              SIZE      MODIFIED
llama3.1:8b    46e0c10c039e    4.9 GB    x minutes ago
```

---

## Step 7 — Verify Everything Together

Run this checklist top to bottom. Every command should return the expected output before you proceed.

```bash
# 1. Homebrew
brew --version
# Expected: Homebrew 4.x.x

# 2. Git
git --version
# Expected: git version 2.x.x

# 3. Python
python3.12 --version
# Expected: Python 3.12.x

# 4. pip
pip3.12 --version
# Expected: pip 24.x.x

# 5. MongoDB running
brew services list | grep mongodb
# Expected: mongodb-community  started

# 6. Ollama running
curl http://localhost:11434/
# Expected: Ollama is running

# 7. Model available
ollama list
# Expected: llama3.1:8b listed
```

If anything shows an error, refer to the relevant step above and re-run the install command.

---

## Common Issues

**"brew: command not found" after installing Homebrew**
You missed the "Next steps" section printed at the end of the Homebrew install. Go back and run those 2 commands — they add Homebrew to your shell PATH.

**"python3.12: command not found"**
Run `brew link python@3.12 --force` and open a new Terminal window.

**MongoDB fails to start**
Check if port 27017 is already in use by another app:
```bash
lsof -i :27017
```
If something is listed, stop that process first. If nothing is listed, try reinstalling: `brew reinstall mongodb-community`.

**Ollama model download stops / fails**
Re-run `ollama pull llama3.1:8b` — it resumes from where it left off.

**"Error: ollama server not responding"**
Ollama service isn't running. Start it:
```bash
brew services start ollama
```

---

## Optional — Code Editor

If you plan to read or modify the agent's code, install **Visual Studio Code** — a free, beginner-friendly editor.

```bash
brew install --cask visual-studio-code
```

Or download directly from: https://code.visualstudio.com

---

## Summary

Once all steps are done, your machine has:

- [x] Homebrew — package manager
- [x] Git — source control
- [x] Python 3.12 — runtime
- [x] MongoDB — local database (running as a background service)
- [x] Ollama — local AI model runner (running as a background service)
- [x] llama3.1:8b — AI model downloaded and ready

You are ready to set up the project. Proceed to `SETUP.md`.
