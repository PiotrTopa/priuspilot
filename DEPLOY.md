# PriusPilot Deployment Guide — Pocophone F1

## Build Artifacts

| Artifact | Path | Size |
|----------|------|------|
| APK (signed release) | `android/build/outputs/apk/release/android-release.apk` | ~92 MB |
| Pyboard firmware | `panda/board/obj/panda_pyboard.bin.signed` | ~50 KB |

## Prerequisites

- Pocophone F1 with existing flowpilot + Termux + proot Ubuntu installed
- Phone in Developer Mode with USB debugging enabled
- USB cable for ADB (initial setup), WiFi for SSH (ongoing development)
- WSL2: use `usbipd bind/attach` to pass USB to Linux

## SSH Access to Termux (recommended for development)

SSH over WiFi is the primary way to deploy backend changes. It avoids the
`adb forward` instability that crashes usbipd on WSL2.

### First-time setup

1. **Connect ADB** (USB, with usbipd on WSL2):

        export PATH="$HOME/android-sdk/platform-tools:$PATH"
        adb devices

   If `no permissions`, fix USB access:

        sudo chmod 666 /dev/bus/usb/001/*
        adb kill-server && adb devices

2. **Grant Termux storage permission** (needed to read scripts from `/sdcard`):

        adb shell pm grant com.termux android.permission.READ_EXTERNAL_STORAGE
        adb shell pm grant com.termux android.permission.WRITE_EXTERNAL_STORAGE

3. **Generate SSH key** (on WSL2, if not already done):

        ssh-keygen -t ed25519 -f ~/.ssh/id_ed25519 -N ""

4. **Push key and setup script to phone**:

        adb push ~/.ssh/id_ed25519.pub /sdcard/flowpilot/id_ed25519.pub
        # Create setup script
        cat > /tmp/setup_termux_ssh.sh << 'SCRIPT'
        #!/data/data/com.termux/files/usr/bin/bash
        pkg install -y openssh 2>/dev/null
        ssh-keygen -A 2>/dev/null
        mkdir -p ~/.ssh
        cat /sdcard/flowpilot/id_ed25519.pub >> ~/.ssh/authorized_keys
        chmod 600 ~/.ssh/authorized_keys
        SSHD_CONFIG="$PREFIX/etc/ssh/sshd_config"
        grep -q "^ListenAddress" "$SSHD_CONFIG" 2>/dev/null && \
            sed -i 's/^ListenAddress.*/ListenAddress 0.0.0.0/' "$SSHD_CONFIG" || \
            echo "ListenAddress 0.0.0.0" >> "$SSHD_CONFIG"
        grep -q "^PubkeyAuthentication" "$SSHD_CONFIG" 2>/dev/null || \
            echo "PubkeyAuthentication yes" >> "$SSHD_CONFIG"
        pkill sshd 2>/dev/null; sleep 1; sshd
        echo "SSH_SETUP_DONE" > /sdcard/flowpilot/ssh_result.txt
        SCRIPT
        adb push /tmp/setup_termux_ssh.sh /sdcard/flowpilot/setup_ssh.sh

5. **Run setup in Termux** (bring Termux to foreground first):

        adb shell am start -n com.termux/.app.TermuxActivity
        sleep 2
        adb shell "input text 'bash /sdcard/flowpilot/setup_ssh.sh'"
        adb shell input keyevent 66    # press Enter

6. **Verify**:

        adb shell cat /sdcard/flowpilot/ssh_result.txt
        # Should say: SSH_SETUP_DONE

7. **Get phone IP**:

        adb shell "ip addr show wlan0 | grep 'inet ' | awk '{print \$2}' | cut -d/ -f1"

8. **Add to `~/.ssh/config`**:

        # PriusPilot - Pocophone F1 (Termux SSH)
        Host pocophone
            HostName 192.168.0.14    # <-- your phone's WiFi IP
            Port 8022
            IdentityFile ~/.ssh/id_ed25519
            StrictHostKeyChecking no
            UserKnownHostsFile /dev/null
            LogLevel ERROR

9. **Test**:

        ssh pocophone "whoami && echo OK"

> **Note**: Termux sshd starts automatically via the `boot_flowpilot` script.
> If sshd is not running, open Termux and type `sshd`.

### Paths on the phone

| What | Path |
|------|------|
| Termux home | `/data/data/com.termux/files/home` |
| Proot root | `$PREFIX/var/lib/proot-distro/installed-rootfs/ubuntu-jammy-fd` |
| Proot flowpilot | `$PREFIX/var/lib/proot-distro/installed-rootfs/ubuntu-jammy-fd/root/flowpilot` |
| Shared storage | `/sdcard/flowpilot/` |

## Deploy Backend Changes (Python/capnp)

Use the deploy script over SSH:

    ./scripts/deploy-to-phone.sh            # uses "pocophone" SSH host
    ./scripts/deploy-to-phone.sh myhost     # custom SSH host

Or manually via scp:

    PROOT_FP='$PREFIX/var/lib/proot-distro/installed-rootfs/ubuntu-jammy-fd/root/flowpilot'
    scp selfdrive/thermald/thermald.py pocophone:$PROOT_FP/selfdrive/thermald/
    scp cereal/log.capnp pocophone:$PROOT_FP/cereal/

## Install APK (UI/Android changes)

Build and install:

    export JAVA_HOME=/usr/lib/jvm/java-11-openjdk-amd64
    export ANDROID_HOME=$HOME/android-sdk
    export PATH="$ANDROID_HOME/platform-tools:$PATH"
    ./gradlew android:assembleRelease -PandroidSlim
    adb install -r android/build/outputs/apk/release/android-release.apk

If signature mismatch (first install from our fork):

    adb uninstall ai.flow.android
    adb install android/build/outputs/apk/release/android-release.apk

## Restart Flowpilot

    adb shell am force-stop ai.flow.android
    adb shell am force-stop com.termux
    adb shell am start -n ai.flow.android/ai.flow.android.LoadingActivity

Or via SSH:

    ssh pocophone "pkill -f launch_flowpilot"
    # Then relaunch the app on the phone

## Pyboard Firmware Flashing

Flash from WSL2 (not the phone). Put Pyboard in DFU mode (BOOT0 jumper).

    sudo apt install dfu-util
    cd panda/board
    dfu-util -a 0 -s 0x08004000:leave -D obj/panda_pyboard.bin.signed

## Full Rebuild Commands

    cd /home/piotr/projects/priuspilot/flowpilot

    # Panda firmware
    cd panda && scons board/obj/panda_pyboard.bin.signed && cd ..

    # APK
    export JAVA_HOME=/usr/lib/jvm/java-11-openjdk-amd64
    export ANDROID_HOME=$HOME/android-sdk
    ./gradlew android:assembleRelease -PandroidSlim

    # Regenerate Java defs (if .capnp schemas change)
    capnpc --src-prefix=cereal cereal/log.capnp cereal/car.capnp cereal/legacy.capnp \
        -ojava:cereal/java/ai.flow.definitions
