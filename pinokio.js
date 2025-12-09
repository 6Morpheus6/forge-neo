const path = require('path')
module.exports = {
  version: "2.0",
  title: "Forge Neo",
  description: "[NVIDIA ONLY] Stable Diffusion WebUI Forge supporting Flux, Qwen, wan, nunchaku and more in a lightweight WebUI. https://github.com/Haoming02/sd-webui-forge-classic/tree/neo",
  icon: "icon.jpeg",
  menu: async (kernel, info) => {
    let installed = info.exists("app/venv")
    
    let downloading = [
      "download-wan2_1-t2v-1_3B.json",
      "download-wan2_2-t2v-14B.json",
      "download-wan2_2-i2v-14B.json",
      "download-z-image-turbo.json",
      "download-neta-lumina.json",
      "download-netayume-lumina.json",
      "download-qwen-image.json",
      "download-qwen-image-edit.json",
      "download-flux1-dev-nf4-v2.json",
      "download-flux1-schnell-nf4.json",
      "download-flux1-dev-fp8.json",
      "download-flux-kontext.json",
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
            { text: "Wan2.1-1.3B Text2Vid", icon: "fa-solid fa-download", href: "download-wan2_1-t2v-1_3B.json", mode: "refresh" },
            { text: "Wan2.2-14B Text2Vid", icon: "fa-solid fa-download", href: "download-wan2_2-t2v-14B.json", mode: "refresh" },
            { text: "Wan2.2-14B Img2Vid", icon: "fa-solid fa-download", href: "download-wan2_2-i2v-14B.json", mode: "refresh" },
            { text: "Z-Image Turbo", icon: "fa-solid fa-download", href: "download-z-image-turbo.json", mode: "refresh" },
            { text: "Lumina v1.0", icon: "fa-solid fa-download", href: "download-neta-lumina.json", mode: "refresh" },
            { text: "Lumina v2.0", icon: "fa-solid fa-download", href: "download-netayume-lumina.json", mode: "refresh" },
            { text: "Qwen Image", icon: "fa-solid fa-download", href: "download-qwen-image.json", mode: "refresh" },
            { text: "Qwen Image Edit", icon: "fa-solid fa-download", href: "download-qwen-image-edit.json", mode: "refresh" },
            { text: "FLUX1-Dev-fp8", icon: "fa-solid fa-download", href: "download-flux1-dev-fp8.json", mode: "refresh" },
            { text: "FLUX1-Dev-nf4-v2", icon: "fa-solid fa-download", href: "download-flux1-dev-nf4-v2.json", mode: "refresh" },
            { text: "FLUX1-Schnell-nf4", icon: "fa-solid fa-download", href: "download-flux1-schnell-nf4.json", mode: "refresh" },
            { text: "FLUX-Kontext", icon: "fa-solid fa-download", href: "download-flux-kontext.json", mode: "refresh" },
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
