
# Tinxy Home Assistant Integration

Integrate [Tinxy.in](https://tinxy.in/) smart switches and devices with Home Assistant using this custom component.

## Overview

This repository provides a Home Assistant integration for Tinxy smart devices, allowing you to control switches, fans, lights, and locks directly from Home Assistant.

## Installation

### 1. Install HACS
HACS is a community app store for Home Assistant. Follow the [HACS setup guide](https://hacs.xyz/docs/setup/prerequisites) to install.

### 2. Add Repository to HACS
Once HACS is installed:
1. Navigate to **HACS → Integrations**.
   <img src="https://user-images.githubusercontent.com/693151/220521463-ff3b6de5-0abd-4f15-81cb-0a4663e3991a.png" width="400"/>
2. Click the three dots at the top right and select **Custom repositories**.
   <img src="https://user-images.githubusercontent.com/693151/220522658-5c196e7e-82d7-422c-9e67-15a5e9c7d139.png" width="250"/>
3. Paste `https://github.com/arevindh/tinxy-hacs`, select **Integration**, and click **Add**.
   <img src="https://user-images.githubusercontent.com/693151/220522068-aeb2423a-5d78-4318-a181-1037b2299a7b.png" width="400"/>
4. Close the Custom repositories section.
5. Click **Explore & Download** at the bottom right.
   ![image](https://user-images.githubusercontent.com/693151/220522243-48b85c0f-59ff-45f6-b664-37157eb1ec15.png)
6. Search for `Tinxy`, then add and install it.
7. Restart Home Assistant.

## Usage

1. **Get API Key:**
   - Obtain your API key from the Tinxy mobile application.
2. **Configure Integration:**
   - Go to **Settings → Integrations** in Home Assistant.
   - Search for "Tinxy" and click on it.
   - ![screen-1](https://user-images.githubusercontent.com/693151/220121949-4f48a2ad-bae5-42e9-9167-b6bc8f524251.png)
   - Enter your API key and click **Submit**.
   - ![screen-2](https://user-images.githubusercontent.com/693151/220121597-624f3abf-2d28-4ca9-8764-0fb9e819e138.png)
   - Click **Finish** on the next screen.
   - You can find all devices in the integration screen.

## Configuration

- You can adjust the `scan_interval` parameter to change how often device status is updated. It is recommended to keep this above `7` seconds to avoid slowing down your Home Assistant server.

## Known Issues

- Due to response delays from the Tinxy API, toggling devices may have a delay of approximately 3 seconds.

## License

See [LICENSE](LICENSE) for details.

