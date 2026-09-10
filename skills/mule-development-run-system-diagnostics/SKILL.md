---
name: run-system-diagnostics
description: Run ACB (Anypoint Code Builder) system diagnostics to check if the machine meets minimum specifications and apply Windows optimizations if needed
metadata:
  author: mule-dx-tooling
  version: "1.0.0"
---

# ACB System Diagnostics

This skill checks if the user's system meets the minimum specifications for Anypoint Code Builder and applies necessary Windows optimizations.

## Minimum Specifications
- **CPU**: 8 cores/8 vCPU
- **RAM**: 32GB
- **Storage Type**: NVMe SSD (PCIe 3.0+)
- **Free Disk Space**: 50GB
- **Network Speed**: 1Gbps

## Steps

## Step 1: Detect Operating System
- Identify if the user is on Windows, macOS, or Linux

## Step 2: Gather System Information
- CPU: Number of cores/vCPUs
- RAM: Total memory in GB
- Storage Type: Verify the storage uses NVMe standard (must be NVMe, not SATA SSD or HDD)
- Free Disk Space: Available space in GB
- Network Speed: Network interface speed

**For Windows systems, use these PowerShell commands:**
- **CPU & RAM Info**: `powershell.exe -Command "Get-ComputerInfo | Select-Object CsProcessors, CsTotalPhysicalMemory, OsArchitecture"`
- **Logical Processors**: `powershell.exe -Command "(Get-WmiObject -Class Win32_Processor).NumberOfLogicalProcessors"`
- **Storage Info**: `powershell.exe -Command "Get-PhysicalDisk | Select-Object MediaType, BusType, Size, FriendlyName"`
- **Disk Space**: `powershell.exe -Command "Get-PSDrive C | Select-Object Used, Free"`
- **Network Speed**: `powershell.exe -Command "Get-NetAdapter | Select-Object Name, Status, LinkSpeed"`

**For macOS systems, use these commands:**
- **CPU Cores**: `sysctl -n hw.physicalcpu && sysctl -n hw.logicalcpu`
  - Returns physical and logical cores (use logical for comparison)
- **RAM**: `sysctl -n hw.memsize`
  - Returns bytes, divide by 1073741824 to get GB
- **Disk Space**: `df -h /`
  - Shows total, used, and available disk space
- **Storage Type (NVMe)**: `system_profiler SPNVMeDataType`
  - Shows NVMe SSD details including model, capacity, and TRIM support
- **Network Hardware**: `networksetup -listallhardwareports`
  - Lists all network interfaces
- **Wi-Fi Status**: `ifconfig en0 | grep 'status:' && networksetup -getinfo Wi-Fi`
  - Shows if Wi-Fi is active and configuration details
- **Wi-Fi PHY Mode**: `system_profiler SPAirPortDataType | grep -A 10 "Current Network Information" | grep -E "Link Speed|PHY Mode"`
  - Shows Wi-Fi standard (802.11ax = Wi-Fi 6, etc.)

## Step 3: Compare Against Minimum Specifications
- For each component, indicate if it meets (✓) or fails (✗) the minimum requirement
- **IMMEDIATELY after gathering system info, display** a clear summary table showing:
  - Component
  - Current Value
  - Minimum Required
  - Status (Pass/Fail)
- Do not wait until the end of the skill to show this table

## Step 4: Windows-Specific Optimizations
(only if on Windows)

#### A. IOPS Performance Test
- **Locate DiskSpd executable:**
  - Detect the processor architecture (amd64, arm64, or x86)
  - Use the appropriate diskspd.exe from the skill's assets folder (relative to the skill base directory):
    - For amd64: `{skill_base_directory}/assets/DiskSpd/amd64/diskspd.exe`
    - For arm64: `{skill_base_directory}/assets/DiskSpd/arm64/diskspd.exe`
    - For x86: `{skill_base_directory}/assets/DiskSpd/x86/diskspd.exe`
  - **If the DiskSpd assets folder or the required diskspd.exe is missing, download and extract it:**
    - **Before downloading, inform the user in one concise sentence** what is being downloaded and why, e.g. "Fetching Microsoft's DiskSpd utility from the official GitHub release to benchmark your disk's IOPS performance."
    - Download URL: `https://github.com/microsoft/diskspd/releases/download/v2.2/DiskSpd.ZIP`
    - Target location: `{skill_base_directory}/assets/DiskSpd/`
    - Use PowerShell to download and extract:
      ```powershell
      $target = "{skill_base_directory}/assets/DiskSpd"
      $zip = Join-Path $env:TEMP "DiskSpd.ZIP"
      New-Item -ItemType Directory -Force -Path $target | Out-Null
      Invoke-WebRequest -Uri "https://github.com/microsoft/diskspd/releases/download/v2.2/DiskSpd.ZIP" -OutFile $zip -UseBasicParsing
      Expand-Archive -Path $zip -DestinationPath $target -Force
      Remove-Item $zip -Force
      ```
    - After extraction, verify that `diskspd.exe` exists under the architecture-specific subfolder (`amd64`, `arm64`, or `x86`)
    - If the download fails (no network, proxy issues, etc.), inform the user clearly, provide the download URL, and skip the IOPS test rather than failing the whole skill
- **Create Test File:**
  - Command: `diskspd.exe -c1G testfile.dat`
  - This creates a 1GB test file required for IOPS testing
  - Note: DiskSpd requires a pre-existing file to test against
- **Run Random Read IOPS Test:**
  - Command: `diskspd.exe -b4K -d30 -o32 -t4 -r -w0 -Sh testfile.dat`
  - This tests random read IOPS with 4KB blocks for 30 seconds
  - Requirement: ≥10,000 IOPS
- **Run Random Write IOPS Test:**
  - Command: `diskspd.exe -b4K -d30 -o32 -t4 -r -w100 -Sh testfile.dat`
  - This tests random write IOPS with 4KB blocks for 30 seconds
  - Requirement: ≥8,000 IOPS
- **Parse and Display Results:**
  - Extract the IOPS values from the DiskSpd output
  - Compare against minimum requirements:
    - Random Read: 10,000 IOPS minimum
    - Random Write: 8,000 IOPS minimum
  - **IMMEDIATELY display a table** with the read and write IOPS result and Pass/Fail status
  - If tests fail, provide guidance on storage improvements
- **Clean up:**
  - Delete the testfile.dat after testing

#### B. Microsoft Defender Exclusions
- **First, check current exclusions:**
  - Use PowerShell to check existing process exclusions: `Get-MpPreference | Select-Object -ExpandProperty ExclusionProcess`
  - Use PowerShell to check existing path exclusions: `Get-MpPreference | Select-Object -ExpandProperty ExclusionPath`
  - Detect the current user's username dynamically
  - Compare current exclusions against recommended exclusions:
    - Process exclusions: `java.exe`, `javaw.exe`, `node.exe`, `Code.exe`
    - Path exclusions (use current username):
      - `C:\Users\<USERNAME>\AnypointCodeBuilder`
      - `C:\Users\<USERNAME>\.vscode`
      - `C:\Users\<USERNAME>\.m2`
      - `C:\Users\<USERNAME>\AppData\Local\Temp`
- **Determine what's missing:**
  - Identify which processes are NOT already excluded
  - Identify which paths are NOT already excluded
  - If all exclusions already exist, inform the user and skip this step
- **Ask for user permission (only if exclusions are missing):**
  - Show the user which specific files/paths are not yet excluded
  - Explain why these exclusions improve ACB performance (reduces scanning overhead)
  - Ask if the user wants to add the missing exclusions
  - Allow the user to decline
- **Apply exclusions (only if user agrees):**
  - Run PowerShell commands to add missing exclusions:
    - Use `Add-MpPreference -ExclusionProcess` for executables
    - Use `Add-MpPreference -ExclusionPath` for directories
  - Handle admin privilege errors:
    - If commands fail due to insufficient privileges, catch the error
    - Inform the user they need administrator privileges
    - Provide the exact commands they should ask their admin to run
    - Do not show scary error messages, just explain clearly what's needed

#### C. Power Plan Analysis
- Check the current active power plan using: `powershell.exe -Command "powercfg /getactivescheme"`
- Display the current power plan to the user
- Analyze if the current power plan is sufficient for ACB:
  - **High Performance**: ✓ Optimal for ACB - no change needed
  - **Balanced**: ⚠ May impact ACB performance - recommend switching to High Performance
  - **Power Saver**: ✗ Not recommended for ACB - strongly recommend switching to High Performance
- If the current plan is not High Performance:
  - Explain why High Performance is recommended for ACB
  - Ask the user if they want to switch to High Performance
  - Provide the command: `powercfg /setactive SCHEME_MIN` (requires admin)
  - Allow the user to skip this step if they choose
- If the current plan is already High Performance, inform the user and skip this step

## Step 5: Output Format
- Present findings in a clear, formatted table
- For Windows systems, provide clear status of optimization steps
- For power plan: display current plan, provide analysis, and ask for user confirmation before making changes
- If admin privileges are required, inform the user and provide the exact commands they need to run
- If any specification is not met, highlight it clearly and suggest potential solutions
- Respect user choices to skip optional optimization steps

## Important Notes
- Windows optimizations require administrator privileges
- Always verify system information before making changes
- Provide clear feedback on what was checked and what actions were taken
- For non-Windows systems (macOS, Linux), do NOT mention Windows-specific optimizations at all