"""
Auto_Metadata_Ksampler_Stamp by Steve Lasmin
============================================
A ComfyUI custom node that automatically extracts KSampler metadata
from the workflow JSON and stamps it onto the bottom of generated images.

Author: Steve Lasmin (Eklipsis)
GitHub: https://github.com/Eklipsis/auto_metadata_ksampler_stamp_by_steve_lasmin
Support: https://boosty.to/stevelasmin
Email: real.eclipse@gmail.com

License: Free to use, but cannot be modified without explicit approval.
"""

import torch
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import os


class AutoMetadataKSamplerStamp:
    """
    Auto_Metadata_Ksampler_Stamp by Steve Lasmin

    Automatically extracts KSampler metadata from the ComfyUI workflow JSON
    and stamps it onto the bottom of the generated image as readable text.

    The node uses the hidden `PROMPT` input to access the full workflow JSON,
    traces KSampler connections back to CLIPTextEncode nodes, and renders
    Seed, Steps, CFG, Denoise, Sampler, Scheduler, Positive and Negative prompts
    onto a black padding bar at the bottom of the image.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image": ("IMAGE",),
            },
            "hidden": {
                "prompt": "PROMPT",
                "unique_id": "UNIQUE_ID"
            }
        }

    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("stamped_image",)
    FUNCTION = "stamp_metadata"
    CATEGORY = "image/stamping"
    DESCRIPTION = "Extracts KSampler settings from workflow and stamps metadata text onto the image"

    def stamp_metadata(self, image, prompt=None, unique_id=None):
        # Extract image dimensions
        if image.dim() == 4:
            B, H, W, C = image.shape
        else:
            raise ValueError("Expected image tensor in BHWC format")

        # Parse workflow JSON for KSampler nodes
        samplers_data = self._extract_sampler_data(prompt)

        # Build text lines array
        text_lines = [f"Image Resolution: {W}x{H}"]

        if not samplers_data:
            text_lines.append("No KSampler data found in workflow.")
        else:
            for i, data in enumerate(samplers_data):
                if len(samplers_data) > 1:
                    text_lines.append(f"--- KSampler {i+1} (Node ID: {data['node_id']}) ---")
                else:
                    text_lines.append("--- KSampler Settings ---")

                text_lines.append(
                    f"Seed: {data['seed']} | Steps: {data['steps']} | CFG: {data['cfg']} | Denoise: {data['denoise']}"
                )
                text_lines.append(f"Sampler: {data['sampler_name']} | Scheduler: {data['scheduler']}")
                text_lines.append(f"Positive: {data['positive']}")
                text_lines.append(f"Negative: {data['negative']}")

        # Process each image in the batch
        images_out = []
        for img in image:
            # Convert tensor (H, W, C) to PIL Image
            img_np = (img.cpu().numpy() * 255).astype(np.uint8)
            pil_img = Image.fromarray(img_np)

            # Dynamic font sizing based on image width
            font_size = max(12, int(W / 60))
            font = self._get_font(font_size)

            margin = 10
            max_text_width = W - (2 * margin)

            # Word-wrap text to fit within image width
            draw = ImageDraw.Draw(pil_img)
            wrapped_lines = []

            for line in text_lines:
                sublines = line.split('\n')
                for subline in sublines:
                    words = subline.split(' ')
                    current_line = ""
                    for word in words:
                        if not word:
                            continue
                        test_line = (current_line + " " + word).strip() if current_line else word
                        try:
                            line_width = draw.textlength(test_line, font=font)
                        except Exception:
                            line_width = 0

                        if line_width <= max_text_width:
                            current_line = test_line
                        else:
                            if current_line:
                                wrapped_lines.append(current_line)
                            current_line = word
                    if current_line:
                        wrapped_lines.append(current_line)

            # Calculate padding height
            line_height = font_size + 4
            total_text_height = len(wrapped_lines) * line_height + (2 * margin)

            # Create new canvas with black padding at bottom
            new_img = Image.new("RGB", (W, H + total_text_height), (0, 0, 0))
            new_img.paste(pil_img, (0, 0))

            # Draw white text on black padding
            draw = ImageDraw.Draw(new_img)
            y_text = H + margin
            for line in wrapped_lines:
                draw.text((margin, y_text), line, font=font, fill=(255, 255, 255))
                y_text += line_height

            # Convert back to ComfyUI tensor (H, W, C)
            out_np = np.array(new_img).astype(np.float32) / 255.0
            out_tensor = torch.from_numpy(out_np)
            images_out.append(out_tensor)

        # Stack batch
        output_tensor = torch.stack(images_out)
        return (output_tensor,)

    def _extract_sampler_data(self, prompt):
        """Scans workflow JSON for KSampler nodes and traces inputs to CLIPTextEncode."""
        if not prompt:
            return []

        # Supported KSampler class types (exact matches only)
        sampler_types = {
            "KSampler",
            "KSamplerAdvanced",
            "KSampler (Efficient)",
            "KSamplerSelect",
            "SamplerCustom",
            "SamplerEulerAncestral",
            "SamplerEuler",
            "SamplerDPMPP2SAncestral",
            "SamplerDPMPPSDE",
            "SamplerDPMPP2M",
            "SamplerDPMAdaptive",
            "SamplerLMS",
            "SamplerHeun",
            "SamplerDPM2",
            "SamplerDPM2Ancestral",
            "SamplerDPMFast",
            "SamplerBPMD",
            "SamplerDEIS",
            "SamplerIPNDM",
            "SamplerDPMPP_SDE",
            "SamplerDPMPP_2M",
            "SamplerDPMPP_2S_Ancestral",
            "KSampler SDXL",
            "KSampler Tiled",
            "KSampler Inpaint",
            "KSamplerCrop",
            "KSamplerSimple",
            "KSamplerWithRefiner",
            "KSamplerDual",
            "KSamplerRestart",
            "KSamplerUniPC",
            "KSamplerDPMFast",
            "KSamplerDPM2",
            "KSamplerDPM2Ancestral",
            "KSamplerDPM2Karras",
            "KSamplerDPM2AncestralKarras",
            "KSamplerLMS",
            "KSamplerLMSKarras",
            "KSamplerEuler",
            "KSamplerEulerAncestral",
            "KSamplerHeun",
            "KSamplerHeunKarras",
            "KSamplerDPMFast",
            "KSamplerDPMAdaptive",
            "KSamplerDPPSDE",
            "KSamplerDPMSDE",
        }

        samplers_data = []

        for node_id, node_info in prompt.items():
            class_type = node_info.get("class_type", "")

            # Only match exact known sampler types, or types that START with "KSampler"
            is_sampler = class_type in sampler_types or class_type.startswith("KSampler")

            if not is_sampler:
                continue

            inputs = node_info.get("inputs", {})

            # Validate: a real KSampler MUST have at least 'steps' and 'cfg' inputs
            if "steps" not in inputs and "cfg" not in inputs:
                continue

            data = {
                'node_id': node_id,
                'seed': inputs.get('seed', inputs.get('noise_seed', 'N/A')),
                'steps': inputs.get('steps', 'N/A'),
                'cfg': inputs.get('cfg', 'N/A'),
                'sampler_name': inputs.get('sampler_name', 'N/A'),
                'scheduler': inputs.get('scheduler', 'N/A'),
                'denoise': inputs.get('denoise', 'N/A'),
                'positive': self._get_text_from_link(prompt, inputs.get('positive')),
                'negative': self._get_text_from_link(prompt, inputs.get('negative'))
            }
            samplers_data.append(data)

        return samplers_data

    def _get_text_from_link(self, prompt, link):
        """Traces a KSampler positive/negative link back to CLIPTextEncode or similar text nodes."""
        if not link or not isinstance(link, list):
            return str(link) if link else "N/A"

        node_id = str(link[0])
        if node_id in prompt:
            node = prompt[node_id]
            inputs = node.get("inputs", {})

            # Direct text input
            if "text" in inputs:
                return inputs["text"]

            # CLIPTextEncode SDXL (has text_g and text_l)
            if "text_g" in inputs:
                g_text = inputs.get("text_g", "")
                l_text = inputs.get("text_l", "")
                if g_text == l_text:
                    return g_text
                return f"G: {g_text} | L: {l_text}"

            # ConditioningCombine / ConditioningAverage / etc
            if "conditioning_1" in inputs or "conditioning_to" in inputs:
                return f"Conditioning mix from: {node.get('class_type', 'Unknown')}"

            # GLIGEN / other special nodes
            if "clip" in inputs and "text" not in inputs:
                return f"Connected to: {node.get('class_type', 'Unknown')}"

            # Fallback
            return f"Connected to: {node.get('class_type', 'Unknown')}"

        return "N/A"

    def _get_font(self, size):
        """Attempts to load a system TrueType font, falls back to default."""
        font_paths = [
            "arial.ttf",
            "C:\\Windows\\Fonts\\arial.ttf",
            "C:\\Windows\\Fonts\\segoeui.ttf",
            "C:\\Windows\\Fonts\\calibri.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
            "/usr/share/fonts/truetype/freefont/FreeSans.ttf",
            "/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf",
            "/System/Library/Fonts/Helvetica.ttc",
            "/System/Library/Fonts/SFNSText.ttf",
            "/Library/Fonts/Arial.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSansCondensed.ttf",
        ]

        for fp in font_paths:
            try:
                if os.path.exists(fp):
                    return ImageFont.truetype(fp, size)
            except Exception:
                continue

        # Final fallback
        return ImageFont.load_default()


# ComfyUI node registration
NODE_CLASS_MAPPINGS = {
    "AutoMetadataKSamplerStamp": AutoMetadataKSamplerStamp,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "AutoMetadataKSamplerStamp": "Auto_Metadata_Ksampler_Stamp by Steve Lasmin",
}
