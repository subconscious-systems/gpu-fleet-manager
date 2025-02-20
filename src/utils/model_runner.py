from typing import Dict, Any, Optional
import logging
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
from diffusers import StableDiffusionXLPipeline
import gc

logger = logging.getLogger(__name__)

class ModelRunner:
    """Efficient model runner with resource management"""
    
    def __init__(self):
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.loaded_models: Dict[str, Any] = {}
        self.model_configs = {
            "text-generation": {
                "model_id": "mistralai/Mistral-7B-v0.1",
                "type": "text",
                "max_length": 2048
            },
            "image-generation": {
                "model_id": "stabilityai/stable-diffusion-xl-base-1.0",
                "type": "image",
                "max_batch_size": 4
            }
        }
    
    async def run_job(self, job_config: Dict[str, Any]) -> Dict[str, Any]:
        """Run an inference job"""
        try:
            model_type = job_config.get("model_type", "text-generation")
            model_config = self.model_configs.get(model_type)
            
            if not model_config:
                raise ValueError(f"Unsupported model type: {model_type}")
            
            # Load or get cached model
            model = await self._get_model(model_type, model_config)
            
            if model_config["type"] == "text":
                return await self._run_text_generation(model, job_config)
            else:
                return await self._run_image_generation(model, job_config)
                
        except Exception as e:
            logger.error(f"Error running job: {str(e)}")
            raise
    
    async def _get_model(self, model_type: str, config: Dict[str, Any]) -> Any:
        """Get or load a model with efficient resource management"""
        if model_type in self.loaded_models:
            return self.loaded_models[model_type]
        
        try:
            # Clear GPU memory if needed
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
                gc.collect()
            
            if config["type"] == "text":
                model = await self._load_text_model(config["model_id"])
            else:
                model = await self._load_image_model(config["model_id"])
            
            self.loaded_models[model_type] = model
            return model
            
        except Exception as e:
            logger.error(f"Error loading model {model_type}: {str(e)}")
            raise
    
    async def _load_text_model(self, model_id: str) -> Any:
        """Load a text generation model"""
        try:
            tokenizer = AutoTokenizer.from_pretrained(model_id)
            model = AutoModelForCausalLM.from_pretrained(
                model_id,
                torch_dtype=torch.float16 if self.device == "cuda" else torch.float32,
                low_cpu_mem_usage=True,
                device_map="auto"
            )
            return {"model": model, "tokenizer": tokenizer}
        except Exception as e:
            logger.error(f"Error loading text model: {str(e)}")
            raise
    
    async def _load_image_model(self, model_id: str) -> Any:
        """Load an image generation model"""
        try:
            pipe = StableDiffusionXLPipeline.from_pretrained(
                model_id,
                torch_dtype=torch.float16 if self.device == "cuda" else torch.float32,
                use_safetensors=True,
                variant="fp16" if self.device == "cuda" else None
            )
            if self.device == "cuda":
                pipe = pipe.to(self.device)
            return pipe
        except Exception as e:
            logger.error(f"Error loading image model: {str(e)}")
            raise
    
    async def _run_text_generation(self, model: Dict[str, Any], job_config: Dict[str, Any]) -> Dict[str, Any]:
        """Run text generation"""
        try:
            prompt = job_config.get("prompt", "")
            max_length = min(
                job_config.get("max_length", 1024),
                self.model_configs["text-generation"]["max_length"]
            )
            
            inputs = model["tokenizer"](prompt, return_tensors="pt")
            if self.device == "cuda":
                inputs = inputs.to(self.device)
            
            with torch.no_grad():
                outputs = model["model"].generate(
                    **inputs,
                    max_length=max_length,
                    num_return_sequences=1,
                    temperature=job_config.get("temperature", 0.7),
                    top_p=job_config.get("top_p", 0.9)
                )
            
            response = model["tokenizer"].decode(outputs[0], skip_special_tokens=True)
            return {"text": response}
            
        except Exception as e:
            logger.error(f"Error in text generation: {str(e)}")
            raise
    
    async def _run_image_generation(self, model: Any, job_config: Dict[str, Any]) -> Dict[str, Any]:
        """Run image generation"""
        try:
            prompt = job_config.get("prompt", "")
            negative_prompt = job_config.get("negative_prompt", "")
            
            image = model(
                prompt=prompt,
                negative_prompt=negative_prompt,
                num_inference_steps=job_config.get("steps", 30),
                guidance_scale=job_config.get("guidance_scale", 7.5)
            ).images[0]
            
            # Convert to base64 for API response
            import io
            import base64
            buffered = io.BytesIO()
            image.save(buffered, format="PNG")
            image_base64 = base64.b64encode(buffered.getvalue()).decode()
            
            return {"image": image_base64}
            
        except Exception as e:
            logger.error(f"Error in image generation: {str(e)}")
            raise
    
    def cleanup(self):
        """Clean up resources"""
        try:
            self.loaded_models.clear()
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            gc.collect()
        except Exception as e:
            logger.error(f"Error in cleanup: {str(e)}")

# Global model runner instance
model_runner = ModelRunner()
