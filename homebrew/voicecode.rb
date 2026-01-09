# typed: false
# frozen_string_literal: true

# Homebrew Formula for VoiceCode
# macOS用の音声入力ツール
class Voicecode < Formula
  include Language::Python::Virtualenv

  desc "Voice input tool for macOS with hotkey, transcription, and LLM post-processing"
  homepage "https://github.com/noricha-vr/voicecode"
  url "https://github.com/noricha-vr/voicecode/archive/refs/tags/v0.1.0.tar.gz"
  # TODO: Update SHA256 after creating release tag v0.1.0
  # Run: ./scripts/generate_formula.sh 0.1.0
  sha256 "0000000000000000000000000000000000000000000000000000000000000000"
  license "MIT"
  head "https://github.com/noricha-vr/voicecode.git", branch: "main"

  depends_on :macos
  depends_on "portaudio"
  depends_on "python@3.13"

  # NOTE: This formula uses pip to install dependencies from PyPI.
  # For a fully vendored formula, use homebrew-pypi-poet to generate
  # resource blocks for all dependencies.

  def install
    # Create virtualenv
    virtualenv_create(libexec, "python3.13")

    # Install dependencies via pip
    system libexec/"bin/pip", "install",
           "pynput>=1.7.6",
           "sounddevice>=0.4.6",
           "numpy>=1.24.0",
           "groq>=0.4.0",
           "openai>=1.0.0",
           "pyperclip>=1.8.2",
           "python-dotenv>=1.0.0",
           "rumps>=0.4.0"

    # Install the main package files
    libexec.install Dir["*.py"]

    # Create wrapper script
    (bin/"voicecode").write <<~EOS
      #!/bin/bash
      export PATH="#{libexec}/bin:$PATH"
      exec "#{libexec}/bin/python" "#{libexec}/main.py" "$@"
    EOS
  end

  def post_install
    # Create settings directory
    settings_dir = Pathname.new(Dir.home)/".voicecode"
    settings_dir.mkpath unless settings_dir.exist?
  end

  def caveats
    <<~EOS
      VoiceCode requires the following macOS permissions:

      1. System Settings > Privacy & Security > Accessibility
      2. System Settings > Privacy & Security > Input Monitoring
      3. System Settings > Privacy & Security > Microphone

      Configure API keys in ~/.voicecode/.env:
        GROQ_API_KEY=your_key
        OPENROUTER_API_KEY=your_key

      Start:
        voicecode

      Auto-start on login:
        brew services start voicecode
    EOS
  end

  service do
    run [opt_bin/"voicecode"]
    keep_alive true
    log_path var/"log/voicecode.log"
    error_log_path var/"log/voicecode.log"
  end

  test do
    assert_path_exists bin/"voicecode"
    assert_predicate bin/"voicecode", :executable?
  end
end
