"""
Generate a simple achievement sound and save it to file
This is used to create a simple achievement sound effect when achievements are unlocked
"""

import os
import math
import wave
import struct

def generate_achievement_sound(output_file, duration=0.5):
    """
    Generate a simple achievement sound effect
    
    Args:
        output_file: Path to save the audio file
        duration: Duration of the sound in seconds
    """
    # Audio parameters
    sample_rate = 44100  # Samples per second
    num_samples = int(duration * sample_rate)
    
    # Create directory if it doesn't exist
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    
    # Open WAV file for writing
    with wave.open(output_file, 'w') as wav_file:
        # Set WAV parameters
        wav_file.setparams((1, 2, sample_rate, num_samples, 'NONE', 'not compressed'))
        
        # Generate sound data
        values = []
        
        # First part: Rising tone
        freq_start = 440.0  # Starting frequency in Hz (A4)
        freq_end = 880.0    # Ending frequency in Hz (A5)
        
        for i in range(int(num_samples * 0.4)):
            # Interpolate frequency
            t = i / float(num_samples * 0.4)
            freq = freq_start + t * (freq_end - freq_start)
            
            # Generate sine wave with envelope
            value = int(32767 * math.sin(math.pi * 2 * freq * i / sample_rate) * (0.1 + t * 0.9))
            values.append(struct.pack('h', value))
        
        # Second part: Chord
        freqs = [523.25, 659.25, 783.99]  # C5, E5, G5 (C major chord)
        
        for i in range(int(num_samples * 0.6)):
            t = i / float(num_samples * 0.6)
            envelope = math.exp(-3 * t)  # Exponential decay envelope
            
            # Sum the sine waves for each frequency in the chord
            value = 0
            for freq in freqs:
                value += int(10923 * math.sin(math.pi * 2 * freq * i / sample_rate) * envelope)
            
            values.append(struct.pack('h', max(min(value, 32767), -32767)))
        
        # Write data
        wav_file.writeframes(b''.join(values))

if __name__ == "__main__":
    # Generate achievement sound and save to static folder
    output_path = os.path.join('static', 'sounds', 'achievement.mp3')
    generate_achievement_sound(output_path)
    print(f"Generated achievement sound at {output_path}")
    
    # Generate reward sound (slightly different parameters)
    reward_path = os.path.join('static', 'sounds', 'reward.mp3')
    generate_achievement_sound(reward_path, duration=0.7)
    print(f"Generated reward sound at {reward_path}")