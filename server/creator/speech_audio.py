"""Finalize OpenAI's streamed PCM WAV header before strict asset validation."""
import io
import wave


def finalize_wav(data):
    with wave.open(io.BytesIO(data),'rb') as source:
        rate=source.getframerate()
        channels=source.getnchannels()
        width=source.getsampwidth()
        declared=source.getnframes()
        frames=source.readframes(rate*600+1)
    frame_size=channels*width
    if not frames or len(frames)%frame_size or len(frames)>rate*600*frame_size:
        raise ValueError('Speech WAV is empty, incomplete or over 600 seconds')
    actual=len(frames)//frame_size
    if actual==declared:
        return data
    # A streaming WAV can use a 32-bit sentinel size until the body finishes.
    # Only provider output goes through this function; uploads remain strict.
    if declared*frame_size < 2**31-8:
        raise ValueError('Speech WAV is truncated')
    result=io.BytesIO()
    with wave.open(result,'wb') as target:
        target.setnchannels(channels);target.setsampwidth(width);target.setframerate(rate)
        target.writeframes(frames)
    return result.getvalue()
