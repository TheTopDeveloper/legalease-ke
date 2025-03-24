"""
Generate a simple achievement sound and save it to file
This is used to create a simple achievement sound effect when achievements are unlocked
"""

import math
import wave
import struct
import os

def generate_achievement_sound(output_file, duration=0.5):
    """
    Generate a simple achievement sound effect
    
    Args:
        output_file: Path to save the audio file
        duration: Duration of the sound in seconds
    """
    # Audio parameters
    sample_rate = 44100  # samples per second
    frequency_start = 1200  # Hz
    frequency_end = 2400  # Hz
    
    # Calculate samples
    num_samples = int(duration * sample_rate)
    
    # Create the wave file
    with wave.open(output_file, 'w') as wav_file:
        # Set parameters
        n_channels = 1  # mono
        sample_width = 2  # 2 bytes per sample
        wav_file.setparams((n_channels, sample_width, sample_rate, num_samples, 'NONE', 'not compressed'))
        
        # Create the samples
        for i in range(num_samples):
            t = i / sample_rate  # Time in seconds
            # Linear frequency increase
            freq = frequency_start + (frequency_end - frequency_start) * (t / duration)
            # Apply some amplitude modulation for better effect
            amplitude = 0.7 * math.sin(2 * math.pi * t * 4) ** 2 * 32767
            # Create the sample
            sample = amplitude * math.sin(2.0 * math.pi * freq * t)
            # Write the sample to the file
            packed_sample = struct.pack('h', int(sample))
            wav_file.writeframes(packed_sample)

if __name__ == "__main__":
    # Create the sounds directory if it doesn't exist
    os.makedirs("static/sounds", exist_ok=True)
    # Generate the achievement sound
    generate_achievement_sound("static/sounds/achievement.wav")
    print("Achievement sound created successfully")