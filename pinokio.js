const path = require('path')
module.exports = {
  version: "2.0",
  title: "Forge Neo",
  description: "[NVIDIA ONLY] Stable Diffusion WebUI Forge supporting Flux, Qwen, wan, nunchaku and more in a lightweight WebUI. https://github.com/Haoming02/sd-webui-forge-classic/tree/neo",
  icon: "icon.jpeg",
  menu: async (kernel, info) => {
    let installed = info.exists("app/venv")
    
    let downloading = [
      "download-wan-t2i-1_3B.json",
      "download-qwen.json",
      "download-flux1-dev-nf4-v2.json",
      "download-flux1-schnell-nf4.json",
      "download-flux1-dev-fp8.json",
      "download-sdxl.json",
      "download-sd15.json",
      "download-turbo.json",
      "download-lcm-lora.json",
      "download.json"
    ]
    let is_downloading = null
    for(let item of downloading) {
      let d = info.running(item)
      if (d === true) {
        is_downloading = item
        break;
      }
    }
    let running = {
      install: info.running("install.js"),
      start: info.running("start.js"),
      update: info.running("update.js"),
      reset: info.running("reset.js"),
    }
    if (running.install) {
      return [{
        default: true,
        icon: "fa-solid fa-plug",
        text: "Installing",
        href: "install.js",
      }]
    } else if (installed) {
      if (running.start) {
        let local = info.local("start.js")
        if (local && local.url) {
          return [{
            default: true,
            icon: "fa-solid fa-rocket",
            text: "Open Web UI",
            href: local.url,
          }, {
            icon: 'fa-solid fa-terminal',
            text: "Terminal",
            href: "start.js",
          }]
        } else {
          return [{
            default: true,
            icon: 'fa-solid fa-terminal',
            text: "Terminal",
            href: "start.js",
          }]
        }
      } else if (is_downloading) {
        return [{
          default: true,
          icon: 'fa-solid fa-terminal',
          text: "Downloading",
          href: is_downloading,
        }]
      } else if (running.update) {
        return [{
          default: true,
          icon: 'fa-solid fa-terminal',
          text: "Updating",
          href: "update.js",
        }]
      } else if (running.reset) {
        return [{
          default: true,
          icon: 'fa-solid fa-terminal',
          text: "Resetting",
          href: "reset.js",
        }]
      } else {
        return [{
          default: true,
          icon: "fa-solid fa-power-off",
          text: "Start",
          href: "start.js",
        }, {
          icon: "fa-solid fa-download",
          text: "Download Models",
          menu: [
            { text: "Wan2.1-1.3B Text2Img", icon: "fa-solid fa-download", href: "download-wan-t2i-1_3B.json", mode: "refresh" },
            { text: "Qwen Image", icon: "fa-solid fa-download", href: "download-qwen.json", mode: "refresh" },
            { text: "FLUX1-Dev-fp8", icon: "fa-solid fa-download", href: "download-flux1-dev-fp8.json", mode: "refresh" },
            { text: "FLUX1-Dev-nf4-v2", icon: "fa-solid fa-download", href: "download-flux1-dev-nf4-v2.json", mode: "refresh" },
            { text: "FLUX1-Schnell-nf4", icon: "fa-solid fa-download", href: "download-flux1-schnell-nf4.json", mode: "refresh" },
            { text: "SDXL", icon: "fa-solid fa-download", href: "download-sdxl.json", mode: "refresh" },
            { text: "SDXL Turbo", icon: "fa-solid fa-download", href: "download-turbo.json", mode: "refresh" },
            { text: "SD 1.5", icon: "fa-solid fa-download", href: "download-sd15.json", mode: "refresh" },
            { text: "LCM LoRA", icon: "fa-solid fa-download", href: "download-lcm-lora.json", mode: "refresh" },
            { text: "Download by URL", icon: "fa-solid fa-download", href: "download.html?raw=true" },
          ]
        }, {
          icon: "fa-solid fa-plug",
          text: "Update",
          href: "update.js",
        }, {
          icon: "fa-solid fa-plug",
          text: "Install",
          href: "install.js",
        }, {
          icon: "fa-regular fa-circle-xmark",
          text: "Reset",
          href: "reset.js",
          confirm: "Are you sure you wish to reset the app?"
        }]
      }
    } else {
      return [{
        default: true,
        icon: "fa-solid fa-plug",
        text: "Install",
        href: "install.js",
      }]
    }
  }
}
