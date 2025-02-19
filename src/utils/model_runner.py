from typing import Dict, Optional, Any
import logging
from datetime import datetime
import importlib.util
import sys

logger = logging.getLogger(__name__)

class BaseModelRunner:
    """Base class for model execution, supports basic job processing without ML dependencies"""
    
    def __init__(self):
        self.supports_ml = False
    
    async def run_job(self, job: Any, gpu: Any) -> Dict[str, Any]:
        """Basic job execution without ML features"""
        return {
            "output": "Model execution not supported in base runner",
            "type": "text",
            "metadata": {
                "completed_at": datetime.utcnow().isoformat(),
                "gpu_id": gpu.id if gpu else None,
                "model_name": job.model_name if hasattr(job, 'model_name') else None,
                "supports_ml": False
            }
        }
    
    async def cleanup(self):
        """Cleanup resources"""
        pass

def get_model_runner(model_cache_dir: str = "./model_cache") -> Any:
    """Factory function to get appropriate ModelRunner based on available dependencies"""
    
    # Check if ML dependencies are available
    has_torch = importlib.util.find_spec("torch") is not None
    has_transformers = importlib.util.find_spec("transformers") is not None
    has_diffusers = importlib.util.find_spec("diffusers") is not None
    
    if all([has_torch, has_transformers, has_diffusers]):
        # Import ML-enabled ModelRunner only if dependencies are available
        try:
            from .ml_model_runner import MLModelRunner
            logger.info("Using ML-enabled ModelRunner")
            return MLModelRunner(model_cache_dir)
        except Exception as e:
            logger.warning(f"Failed to initialize ML ModelRunner: {e}")
            return BaseModelRunner()
    else:
        logger.info("Using base ModelRunner (ML features disabled)")
        return BaseModelRunner()

# Only define MLModelRunner if dependencies are available
if all([
    importlib.util.find_spec("torch"),
    importlib.util.find_spec("transformers"),
    importlib.util.find_spec("diffusers")
]):
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer, pipeline
    from diffusers import StableDiffusionXLPipeline
    import asyncio
    
    class MLModelRunner(BaseModelRunner):
        """ML-enabled model runner with full feature support"""
        
        def __init__(self, model_cache_dir: str = "./model_cache"):
            super().__init__()
            self.supports_ml = True
            self.model_cache_dir = model_cache_dir
            self.loaded_models = {}
            self.model_configs = {
                # LLM Models
                "phi-2": {
                    "model_id": "microsoft/phi-2",
                    "type": "text-generation",
                    "max_length": 2048,
                    "temperature": 0.7,
                    "top_p": 0.9
                },
                "deepseek-coder": {
                    "model_id": "deepseek-ai/deepseek-coder-6.7b-instruct",
                    "type": "text-generation",
                    "max_length": 4096,
                    "temperature": 0.7,
                    "top_p": 0.95
                },
                # Stable Diffusion Models
                "stable-diffusion-xl": {
                    "model_id": "stabilityai/stable-diffusion-xl-base-1.0",
                    "type": "image-generation",
                    "guidance_scale": 7.5,
                    "num_inference_steps": 50
                }
            }

        async def run_job(self, job: Any, gpu: Any) -> Dict[str, Any]:
            """Run a model inference job with ML support"""
            try:
                logger.info(f"Starting ML job {job.id} on GPU {gpu.id}")
                
                # Set CUDA device
                torch.cuda.set_device(self._get_gpu_index(gpu))
                
                # Get model configuration
                model_config = self.model_configs.get(job.model_name)
                if not model_config:
                    raise ValueError(f"Unsupported model: {job.model_name}")

                # Load or get cached model
                model_key = f"{job.model_name}_{gpu.id}"
                if model_key not in self.loaded_models:
                    model = await self._load_model(job.model_name, model_config)
                    self.loaded_models[model_key] = model
                else:
                    model = self.loaded_models[model_key]

                # Run inference based on model type
                if model_config["type"] == "text-generation":
                    result = await self._run_text_generation(
                        model,
                        job.input_data,
                        model_config
                    )
                elif model_config["type"] == "image-generation":
                    result = await self._run_image_generation(
                        model,
                        job.input_data,
                        model_config
                    )
                else:
                    raise ValueError(f"Unsupported model type: {model_config['type']}")

                # Add metadata to result
                result["metadata"] = {
                    "completed_at": datetime.utcnow().isoformat(),
                    "gpu_id": gpu.id,
                    "model_name": job.model_name,
                    "supports_ml": True
                }

                return result

            except Exception as e:
                logger.error(f"Error running ML job {job.id}: {e}")
                raise

        async def _load_model(self, model_name: str, config: Dict) -> Any:
            """Load a model and return appropriate pipeline"""
            try:
                logger.info(f"Loading model {model_name}")
                
                if config["type"] == "text-generation":
                    model = AutoModelForCausalLM.from_pretrained(
                        config["model_id"],
                        torch_dtype=torch.float16,
                        device_map="auto",
                        cache_dir=self.model_cache_dir
                    )
                    tokenizer = AutoTokenizer.from_pretrained(
                        config["model_id"],
                        cache_dir=self.model_cache_dir
                    )
                    return pipeline(
                        "text-generation",
                        model=model,
                        tokenizer=tokenizer,
                        device_map="auto"
                    )

                elif config["type"] == "image-generation":
                    return StableDiffusionXLPipeline.from_pretrained(
                        config["model_id"],
                        torch_dtype=torch.float16,
                        use_safetensors=True,
                        variant="fp16",
                        cache_dir=self.model_cache_dir
                    ).to("cuda")

            except Exception as e:
                logger.error(f"Error loading model {model_name}: {e}")
                raise

        async def _run_text_generation(
            self,
            pipeline: Any,
            input_data: Dict,
            config: Dict
        ) -> Dict[str, Any]:
            """Run text generation inference"""
            prompt = input_data.get("prompt")
            if not prompt:
                raise ValueError("No prompt provided for text generation")

            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                lambda: pipeline(
                    prompt,
                    max_length=config["max_length"],
                    temperature=config["temperature"],
                    top_p=config["top_p"],
                    num_return_sequences=1,
                    pad_token_id=pipeline.tokenizer.eos_token_id
                )
            )

            return {
                "output": result[0]["generated_text"],
                "type": "text"
            }

        async def _run_image_generation(
            self,
            pipeline: Any,
            input_data: Dict,
            config: Dict
        ) -> Dict[str, Any]:
            """Run image generation inference"""
            prompt = input_data.get("prompt")
            if not prompt:
                raise ValueError("No prompt provided for image generation")

            negative_prompt = input_data.get("negative_prompt", "")

            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                lambda: pipeline(
                    prompt=prompt,
                    negative_prompt=negative_prompt,
                    guidance_scale=config["guidance_scale"],
                    num_inference_steps=config["num_inference_steps"]
                ).images[0]
            )

            image_bytes = await loop.run_in_executor(
                None,
                lambda: self._convert_image_to_bytes(result)
            )

            return {
                "output": image_bytes,
                "type": "image"
            }

        def _get_gpu_index(self, gpu: Any) -> int:
            """Get CUDA device index from GPU object"""
            return 0

        def _convert_image_to_bytes(self, image) -> bytes:
            """Convert PIL Image to bytes"""
            import io
            img_byte_arr = io.BytesIO()
            image.save(img_byte_arr, format='PNG')
            return img_byte_arr.getvalue()

        async def cleanup(self):
            """Clean up loaded models and free GPU memory"""
            for model in self.loaded_models.values():
                try:
                    model.to("cpu")
                    del model
                except Exception as e:
                    logger.error(f"Error cleaning up model: {e}")
            
            self.loaded_models.clear()
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
