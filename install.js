module.exports = {
  run: [
    {
      method: "shell.run",
      params: {
        message: [
          "git clone -b neo https://github.com/Haoming02/sd-webui-forge-classic app",
        ]
      }
    },
    {
      when: "{{platform === 'win32'}}",
      method: "shell.run",
      params: {
        message: "copy /Y webui-user.bat app\\webui-user.bat",
      }
    },
    {
      when: "{{platform === 'linux'}}",
      method: "shell.run",
      params: {
        message: "cp webui.sh webui-user.sh app/",
      }
    },
    {
      method: "shell.run",
      params: {
        message: "{{platform === 'win32' ? 'webui-user.bat' : 'bash webui.sh -f'}}",
        env: {
          SD_WEBUI_RESTARTING: 1,
        },
        path: "app",
        on: [{ "event": "/http:\/\/[0-9.:]+/", "kill": true }]
      }
    },
    {
      method: "script.start",
      params: {
        uri: "torch.js",
        params: {
          venv: "venv",
          path: "app",
          xformers: true,
          triton: true,
          sageattention: true
        }
      }
    },
    {
      method: "shell.run",
      params: {
        venv: "venv",
        path: "app",
        message: "uv pip install hf-xet"
      }
    },
    {
      id: "share",
      method: "fs.share",
      params: {
        drive: {
          upscale_models: [
            "app/models/ESRGAN",
          ],
          checkpoints: "app/models/Stable-diffusion",
          vae: "app/models/VAE",
          embeddings: "app/models/embeddings",
          clip: "app/models/text_encoder",
          controlnet: "app/models/ControlNet",
          controlnetpreprocessor: "app/models/ControlNetPreprocessor",
          diffusers: "app/models/diffusers",
          loras: "app/models/Lora"
        },
        peers: [
          "https://github.com/cocktailpeanut/fluxgym.git",
          "https://github.com/pinokiofactory/comfy.git",
          "https://github.com/cocktailpeanutlabs/comfyui.git",
          "https://github.com/cocktailpeanutlabs/fooocus.git",
          "https://github.com/cocktailpeanutlabs/automatic1111.git",
        ]
      }
    },
    {
      method: "shell.run",
      params: {
        message: [
          "huggingface-cli download lllyasviel/flux1-dev-bnb-nf4 flux1-dev-bnb-nf4-v2.safetensors --local-dir app/models/Stable-diffusion"
        ]
      }
    },
    {
      method: "fs.share",
      params: {
        drive: {
          outputs: "app/outputs"
        }
      }
    },
  ]
}
