# /// script
# requires-python = ">=3.10"
# ///
"""Opinionated one-command deploy: Telegram bot on a DigitalOcean Droplet.

This is one way to run nanobot -- a single $6/mo droplet with Telegram as
the channel and Honcho for memory. Additional deployment methods, channels,
and hosting options may be added in the future.

Prerequisites:
    brew install doctl && doctl auth init

Usage:
    uv run scripts/deploy.py
    uv run scripts/deploy.py --name my-bot --provider anthropic --model anthropic/claude-sonnet-4-5
"""

import json
import os
import shutil
import subprocess
import sys
import time

REGION = "nyc1"
SIZE = "s-1vcpu-1gb"
IMAGE = "ubuntu-24-04-x64"

PROVIDERS = [
    # (config_name, env_var, default_model, description, help_url)
    ("openrouter",  "OPENROUTER_API_KEY",  "anthropic/claude-sonnet-4-5",      "gateway -- any model",  "https://openrouter.ai/keys"),
    ("anthropic",   "ANTHROPIC_API_KEY",   "anthropic/claude-sonnet-4-5",      "Claude models",         "https://console.anthropic.com"),
    ("openai",      "OPENAI_API_KEY",      "openai/gpt-4o",                    "GPT models",            "https://platform.openai.com/api-keys"),
    ("deepseek",    "DEEPSEEK_API_KEY",    "deepseek/deepseek-chat",           "DeepSeek models",       "https://platform.deepseek.com"),
    ("gemini",      "GEMINI_API_KEY",      "gemini/gemini-2.0-flash",          "Google Gemini",         "https://aistudio.google.com/apikey"),
    ("groq",        "GROQ_API_KEY",        "groq/llama-3.3-70b-versatile",    "fast inference",        "https://console.groq.com/keys"),
]

# filled by choose_provider / choose_model
PROVIDER = {}  # {"name": ..., "env": ..., "key": ..., "model": ...}
OPTIONS = {"fresh": False}  # --fresh: ignore env vars, prompt for everything


def run(cmd, check=True, capture=False, **kw):
    return subprocess.run(cmd, check=check, capture_output=capture, text=True, **kw)

def info(msg): print(f"\033[1m>> {msg}\033[0m")
def ok(msg): print(f"   \033[32m{msg}\033[0m")
def warn(msg): print(f"   \033[33m{msg}\033[0m")
def fail(msg): print(f"   \033[31m{msg}\033[0m"); sys.exit(1)
def dim(msg): print(f"   \033[2m{msg}\033[0m")

def ensure_var(name, prompt, help_text="", required=True):
    if not OPTIONS["fresh"]:
        val = os.environ.get(name, "")
        if val:
            dim(f"{name} set from environment")
            return val
    if help_text: dim(help_text)
    val = input(f"   {prompt}{'' if required else ' (optional)'}: ").strip()
    if not val and required: fail("Value required")
    if val: os.environ[name] = val
    return val

def ssh(ip, cmd, check=True):
    return run(["ssh", "-o", "StrictHostKeyChecking=no", "-o", "ConnectTimeout=10",
                f"root@{ip}", cmd], check=check, capture=True)

def ssh_ok(ip, cmd):
    r = ssh(ip, cmd, check=False)
    return r.returncode == 0


# -- setup ------------------------------------------------------------------

def ensure_doctl():
    info("Checking doctl CLI")
    if shutil.which("doctl"):
        ok("found")
        return
    fail("doctl not found. Install: brew install doctl && doctl auth init")

def ensure_doctl_auth():
    info("Checking doctl auth")
    r = run(["doctl", "account", "get", "--format", "Email,DropletLimit,Status", "--no-header"], check=False, capture=True)
    if r.returncode != 0:
        warn("Not authenticated")
        dim("Run: doctl auth init")
        fail("doctl auth required")
    parts = r.stdout.strip().split()
    if parts:
        email = parts[0]
        ok(f"authenticated ({email})")
        # check droplet limit -- 0 means no billing
        try:
            limit = int(parts[1]) if len(parts) > 1 else -1
        except ValueError:
            limit = -1
        if limit == 0:
            fail("Droplet limit is 0 -- add a payment method at https://cloud.digitalocean.com/account/billing")
    else:
        ok("authenticated")

def get_ssh_key_id():
    info("Finding SSH key")
    r = run(["doctl", "compute", "ssh-key", "list", "--format", "ID,Name", "--no-header"], capture=True)
    lines = r.stdout.strip().split("\n")
    if not lines or not lines[0].strip():
        fail("No SSH keys found in your DO account. Add one: doctl compute ssh-key import")
    key_id = lines[0].split()[0]
    key_name = " ".join(lines[0].split()[1:])
    ok(f"using {key_name} ({key_id})")
    return key_id

def choose_provider():
    info("Provider")
    for i, (name, _env, _model, desc, url) in enumerate(PROVIDERS, 1):
        print(f"   {i}. {name:<14} {desc:<24} {url}")
    choice = input("   Select provider [1]: ").strip() or "1"
    try:
        idx = int(choice) - 1
        if not (0 <= idx < len(PROVIDERS)):
            raise ValueError
    except ValueError:
        fail(f"Invalid choice: {choice}")
    name, env, default_model, desc, url = PROVIDERS[idx]
    PROVIDER["name"] = name
    PROVIDER["env"] = env
    PROVIDER["default_model"] = default_model
    PROVIDER["url"] = url
    ok(f"{name}")

def choose_model():
    info("Model")
    default = PROVIDER["default_model"]
    dim(f"default: {default}")
    choice = input(f"   Model [{default}]: ").strip()
    PROVIDER["model"] = choice if choice else default
    ok(PROVIDER["model"])

def collect_keys():
    info("API keys")
    key = ensure_var(PROVIDER["env"], f"{PROVIDER['name']} API key", PROVIDER["url"])
    PROVIDER["key"] = key
    ensure_var("TELEGRAM_BOT_TOKEN", "Telegram bot token", "@BotFather on Telegram -> /newbot")
    honcho_key = ensure_var("HONCHO_API_KEY", "Honcho API key", "https://app.honcho.dev", required=False)
    if not honcho_key:
        dim("nanobot will start without Honcho -- get your key at app.honcho.dev to activate long-term memory")


# -- droplet ----------------------------------------------------------------

def get_droplet_ip(droplet_name):
    r = run(["doctl", "compute", "droplet", "get", droplet_name, "--format", "PublicIPv4", "--no-header"],
            check=False, capture=True)
    if r.returncode == 0 and r.stdout.strip():
        return r.stdout.strip()
    return None

def create_droplet(droplet_name, ssh_key_id):
    info(f"Creating droplet: {droplet_name}")
    existing_ip = get_droplet_ip(droplet_name)
    if existing_ip:
        ok(f"already exists ({existing_ip})")
        return existing_ip

    cloud_init = """#!/bin/bash
apt-get update -qq
apt-get install -y -qq git curl python3 python3-pip python3-venv > /dev/null 2>&1
curl -LsSf https://astral.sh/uv/install.sh | sh
touch /root/.cloud-init-done
"""
    init_path = "/tmp/nb-cloud-init.yaml"
    with open(init_path, "w") as f:
        f.write(cloud_init)

    run(["doctl", "compute", "droplet", "create", droplet_name,
         "--region", REGION, "--size", SIZE, "--image", IMAGE,
         "--ssh-keys", ssh_key_id, "--user-data-file", init_path,
         "--wait"])

    ip = None
    for _ in range(30):
        ip = get_droplet_ip(droplet_name)
        if ip: break
        time.sleep(2)
    if not ip:
        fail("Could not get droplet IP")
    ok(f"created ({ip})")
    return ip

def wait_for_ssh(ip):
    info("Waiting for SSH")
    for i in range(30):
        if ssh_ok(ip, "echo ok"):
            ok("connected")
            return
        time.sleep(5)
        if i % 3 == 0: dim(f"waiting... ({(i+1)*5}s)")
    fail("SSH timeout")

def wait_for_cloud_init(ip):
    info("Waiting for cloud-init")
    for i in range(60):
        if ssh_ok(ip, "test -f /root/.cloud-init-done"):
            ok("done")
            return
        time.sleep(5)
        if i % 3 == 0: dim(f"waiting... ({(i+1)*5}s)")
    warn("cloud-init may not have finished, continuing anyway")


# -- deploy -----------------------------------------------------------------

def clone_repo(ip, repo, branch):
    info(f"Cloning {repo} @ {branch}")
    ssh(ip, f"rm -rf /root/nanobot && git clone --branch {branch} --single-branch --depth 1 {repo} /root/nanobot")
    ok("cloned")

def install_nanobot(ip):
    info("Installing nanobot")
    ssh(ip, "export PATH=/root/.local/bin:$PATH && cd /root/nanobot && uv venv /root/nanobot/.venv && uv pip install --no-cache -e .")
    nanobot_bin = "/root/nanobot/.venv/bin/nanobot"
    r = ssh(ip, f"test -x {nanobot_bin} && echo ok", check=False)
    if r.stdout.strip() != "ok":
        fail(f"nanobot binary not found at {nanobot_bin}")
    ok(f"installed ({nanobot_bin})")
    return nanobot_bin

def write_config(ip, workspace_id):
    info("Writing config")
    config = {
        "providers": {PROVIDER["name"]: {"apiKey": PROVIDER["key"]}},
        "agents": {"defaults": {"model": PROVIDER["model"]}},
        "channels": {"telegram": {"enabled": True, "token": os.environ["TELEGRAM_BOT_TOKEN"], "allowFrom": []}},
        "honcho": {"enabled": True, "workspaceId": workspace_id, "prefetch": True},
        "tools": {"exec": {"timeout": 60}},
    }
    config_json = json.dumps(config, indent=2)
    ssh(ip, f"mkdir -p /root/.nanobot/workspace && cat > /root/.nanobot/config.json << 'ENDJSON'\n{config_json}\nENDJSON")
    honcho_key = os.environ.get("HONCHO_API_KEY", "")
    if honcho_key:
        ssh(ip, f"echo 'HONCHO_API_KEY={honcho_key}' > /root/.nanobot/.env")
    else:
        ssh(ip, "touch /root/.nanobot/.env")
    ok(f"config.json + .env written ({PROVIDER['name']}/{PROVIDER['model']})")

def setup_service(ip, nanobot_bin):
    info("Setting up systemd service")
    unit = f"""[Unit]
Description=nanobot gateway
After=network.target

[Service]
Type=simple
EnvironmentFile=/root/.nanobot/.env
Environment=PATH=/root/nanobot/.venv/bin:/root/.local/bin:/usr/local/bin:/usr/bin:/bin
ExecStart={nanobot_bin} gateway --port 8080
WorkingDirectory=/root
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
"""
    ssh(ip, f"cat > /etc/systemd/system/nanobot.service << 'EOF'\n{unit}EOF")
    ssh(ip, "systemctl daemon-reload && systemctl enable nanobot && systemctl restart nanobot")
    time.sleep(3)
    r = ssh(ip, "systemctl is-active nanobot", check=False)
    if r.stdout.strip() == "active":
        ok("service running")
    else:
        warn(f"service status: {r.stdout.strip()}")
        r2 = ssh(ip, "journalctl -u nanobot --no-pager -n 20", check=False)
        print(r2.stdout)

def summary(ip, droplet_name, repo, branch, workspace_id):
    print()
    print(f"\033[1m== {droplet_name} deployed ==\033[0m")
    print(f"   IP:        {ip}")
    print(f"   Source:    {repo} @ {branch}")
    print(f"   Provider:  {PROVIDER['name']}")
    print(f"   Model:     {PROVIDER['model']}")
    print(f"   Honcho:    enabled (workspace: {workspace_id})")
    print()
    print(f"   SSH:       ssh root@{ip}")
    print(f"   Status:    ssh root@{ip} systemctl status nanobot")
    print(f"   Logs:      ssh root@{ip} journalctl -u nanobot -f")
    print(f"   Destroy:   doctl compute droplet delete {droplet_name} -f")


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--name", default="nanobot", help="Droplet name (default: nanobot)")
    p.add_argument("--repo", default="https://github.com/plastic-labs/nanobot-honcho.git", help="Git repo URL")
    # TODO: change default to "main" after honcho-default is merged
    p.add_argument("--branch", default="honcho-default", help="Git branch (default: honcho-default)")
    p.add_argument("--workspace", default="nanobot", help="Honcho workspace ID (default: nanobot)")
    p.add_argument("--provider", help="Provider name (openrouter, anthropic, openai, deepseek, gemini, groq)")
    p.add_argument("--provider-key", help="API key for the chosen provider")
    p.add_argument("--model", help="Model identifier (e.g. anthropic/claude-sonnet-4-5)")
    p.add_argument("--telegram-token", help="Telegram bot token")
    p.add_argument("--honcho-key", help="Honcho API key")
    p.add_argument("--fresh", action="store_true", help="Ignore env vars, prompt for everything")
    args = p.parse_args()

    OPTIONS["fresh"] = args.fresh
    DROPLET_NAME = args.name
    REPO = args.repo
    BRANCH = args.branch
    WORKSPACE_ID = args.workspace

    if args.provider:
        match = [prov for prov in PROVIDERS if prov[0] == args.provider]
        if not match: fail(f"Unknown provider: {args.provider}")
        name, env, default_model, desc, url = match[0]
        PROVIDER.update({"name": name, "env": env, "default_model": default_model, "url": url})
        if args.provider_key: os.environ[env] = args.provider_key; PROVIDER["key"] = args.provider_key
        PROVIDER["model"] = args.model or default_model
    if args.telegram_token: os.environ["TELEGRAM_BOT_TOKEN"] = args.telegram_token
    if args.honcho_key: os.environ["HONCHO_API_KEY"] = args.honcho_key

    ensure_doctl()
    ensure_doctl_auth()
    ssh_key_id = get_ssh_key_id()

    if not PROVIDER.get("name"):
        choose_provider()
        choose_model()
    collect_keys()

    ip = create_droplet(DROPLET_NAME, ssh_key_id)
    wait_for_ssh(ip)
    wait_for_cloud_init(ip)
    clone_repo(ip, REPO, BRANCH)
    nanobot_bin = install_nanobot(ip)
    write_config(ip, WORKSPACE_ID)
    setup_service(ip, nanobot_bin)
    summary(ip, DROPLET_NAME, REPO, BRANCH, WORKSPACE_ID)
