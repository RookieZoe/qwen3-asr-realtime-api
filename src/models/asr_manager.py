import asyncio
import torch
import warnings
from typing import Optional, Dict, Any
import os
import sys

# 忽略已知的 vLLM/PyTorch 警告
warnings.filterwarnings("ignore", message="Casting torch.bfloat16 to torch.float16")
warnings.filterwarnings("ignore", message="Please use the new API settings to control TF32")
warnings.filterwarnings("ignore", message="The following generation flags are not valid")
warnings.filterwarnings("ignore", message="We must use the `spawn` multiprocessing start method")
warnings.filterwarnings("ignore", category=UserWarning, module="torch")

sys.path.insert(0, '/home/zoe/ai_lab/workspace/Qwen3-ASR')

from utils.logger import get_logger

logger = get_logger(__name__)


class ASRManager:
    """
    ASR Model Manager for Qwen3-ASR with vLLM backend.
    
    Note: Streaming inference is only available with vLLM backend.
    """
    
    def __init__(self):
        self.model = None
        self.model_path: str = os.getenv("QWEN3_ASR_MODEL_PATH", "/path/to/qwen3-asr-model")
        self.gpu_memory_utilization: float = float(os.getenv("GPU_MEMORY_UTILIZATION", "0.8"))
        self.max_new_tokens: int = int(os.getenv("MAX_NEW_TOKENS", "64"))
        self.dtype: str = os.getenv("MODEL_DTYPE", "auto")
        
    async def load_model(self):
        """
        Load Qwen3-ASR model with vLLM backend for streaming inference.
        """
        logger.info(f"Loading Qwen3-ASR model from {self.model_path}...")
        logger.info(f"vLLM config: gpu_memory_utilization={self.gpu_memory_utilization}, "
                   f"max_new_tokens={self.max_new_tokens}, dtype={self.dtype}")
        
        try:
            from qwen_asr import Qwen3ASRModel
            
            self.model = await asyncio.to_thread(
                Qwen3ASRModel.LLM,
                model=self.model_path,
                gpu_memory_utilization=self.gpu_memory_utilization,
                max_new_tokens=self.max_new_tokens,
                dtype=self.dtype,
                max_model_len=32768,
            )
            
            logger.info("Model loaded successfully with vLLM backend")
        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            raise
    
    async def unload_model(self):
        """Unload model and free GPU memory."""
        if self.model:
            del self.model
            self.model = None
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            logger.info("Model unloaded")
    
    def get_model(self):
        return self.model
    
    def is_ready(self) -> bool:
        return self.model is not None
    
    def init_streaming_state(self, context: str = "", language: Optional[str] = None,
                            unfixed_chunk_num: int = 2, unfixed_token_num: int = 5,
                            chunk_size_sec: float = 2.0):
        """
        Initialize streaming ASR state.
        
        Args:
            context: Context text for the ASR session
            language: Optional language hint (e.g., "Chinese", "English")
            unfixed_chunk_num: Number of initial chunks without prefix
            unfixed_token_num: Number of tokens to rollback for prefix
            chunk_size_sec: Audio chunk size in seconds
        """
        if self.model is None:
            raise RuntimeError("Model not loaded")
        
        return self.model.init_streaming_state(
            context=context,
            language=language,
            unfixed_chunk_num=unfixed_chunk_num,
            unfixed_token_num=unfixed_token_num,
            chunk_size_sec=chunk_size_sec,
        )
    
    def streaming_transcribe(self, pcm16k: Any, state: Any) -> Any:
        """
        Perform streaming transcription on audio chunk.
        
        Args:
            pcm16k: 16kHz mono PCM audio (numpy array)
            state: Streaming state object
            
        Returns:
            Updated state object
        """
        if self.model is None:
            raise RuntimeError("Model not loaded")
        
        return self.model.streaming_transcribe(pcm16k, state)
    
    def finish_streaming_transcribe(self, state: Any) -> Any:
        """
        Finish streaming transcription and process remaining audio.
        
        Args:
            state: Streaming state object
            
        Returns:
            Final state with complete transcription
        """
        if self.model is None:
            raise RuntimeError("Model not loaded")
        
        return self.model.finish_streaming_transcribe(state)
