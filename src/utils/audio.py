import base64
import io
import numpy as np
from typing import Union, Optional


def decode_base64_audio(audio_b64: str) -> Optional[bytes]:
    try:
        return base64.b64decode(audio_b64)
    except Exception:
        return None


def decode_pcm_to_numpy(audio_bytes: bytes, sample_rate: int = 16000, 
                        bits: int = 16) -> Optional[np.ndarray]:
    try:
        if bits == 16:
            dtype = np.int16
        elif bits == 32:
            dtype = np.int32
        else:
            return None
        
        audio_array = np.frombuffer(audio_bytes, dtype=dtype)
        
        audio_array = audio_array.astype(np.float32) / (2 ** (bits - 1))
        return audio_array
    except Exception:
        return None


def decode_opus_to_numpy(audio_bytes: bytes, sample_rate: int = 16000) -> Optional[np.ndarray]:
    """Decode Opus audio to numpy array. Requires opuslib (optional dependency)."""
    try:
        import opuslib
        decoder = opuslib.Decoder(sample_rate, 1)
        
        frame_size = int(sample_rate * 0.02)
        
        pcm_data = decoder.decode(audio_bytes, frame_size)
        audio_array = np.frombuffer(pcm_data, dtype=np.int16)
        audio_array = audio_array.astype(np.float32) / 32768.0
        
        return audio_array
    except ImportError:
        raise ImportError(
            "opuslib is required for Opus audio decoding. "
            "Install with: uv sync --extra audio"
        )
    except Exception:
        return None


def resample_audio(audio: np.ndarray, orig_sr: int, target_sr: int) -> np.ndarray:
    if orig_sr == target_sr:
        return audio
    
    try:
        import librosa
        return librosa.resample(audio, orig_sr=orig_sr, target_sr=target_sr)
    except ImportError:
        from scipy import signal
        resampling_factor = target_sr / orig_sr
        num_samples = int(len(audio) * resampling_factor)
        return signal.resample(audio, num_samples)


def bytes_to_numpy(audio_bytes: bytes, audio_format: str, 
                   sample_rate: int = 16000) -> Optional[np.ndarray]:
    audio_format = audio_format.lower()
    
    if audio_format in ['pcm', 'pcm16', 'pcm_s16le']:
        return decode_pcm_to_numpy(audio_bytes, sample_rate, 16)
    elif audio_format in ['pcm32', 'pcm_s32le']:
        return decode_pcm_to_numpy(audio_bytes, sample_rate, 32)
    elif audio_format in ['opus', 'opuslib']:
        return decode_opus_to_numpy(audio_bytes, sample_rate)
    else:
        return decode_pcm_to_numpy(audio_bytes, sample_rate, 16)
