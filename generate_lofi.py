import math
import random
import struct
import wave

SAMPLE_RATE = 44100
DURATION = 35.0  # seconds
NUM_SAMPLES = int(SAMPLE_RATE * DURATION)
BPM = 85.0
BEAT_SEC = 60.0 / BPM
EIGHTH_SEC = BEAT_SEC / 2.0

# Upbeat Lo-Fi Chords (Frequencies in Hz)
# Cmaj7 -> Am7 -> Dm7 -> G13
chords = [
    [261.63, 329.63, 392.00, 493.88],  # Cmaj7
    [220.00, 261.63, 329.63, 392.00],  # Am7
    [146.83, 174.61, 220.00, 261.63],  # Dm7
    [196.00, 246.94, 349.23, 440.00],  # G13
]

bass_notes = [130.81, 110.00, 73.42, 98.00]  # C3, A2, D2, G2

def generate_lofi_track(filename="lofi_beat.wav"):
    left_samples = [0.0] * NUM_SAMPLES
    right_samples = [0.0] * NUM_SAMPLES

    # Vinyl noise
    for i in range(NUM_SAMPLES):
        if random.random() < 0.002:
            pop = (random.random() - 0.5) * 0.05
            left_samples[i] += pop
            right_samples[i] += pop

    # Generate chord progression and bass
    for i in range(NUM_SAMPLES):
        t = i / SAMPLE_RATE
        beat_idx = int(t / BEAT_SEC)
        measure_idx = int(beat_idx / 4)
        chord_idx = measure_idx % len(chords)
        current_chord = chords[chord_idx]
        current_bass = bass_notes[chord_idx]

        # Chord synth (warm sine/saw blend with soft envelope)
        chord_val = 0.0
        pos_in_beat = (t % BEAT_SEC) / BEAT_SEC
        env = math.exp(-pos_in_beat * 1.5)
        for freq in current_chord:
            tone = 0.6 * math.sin(2 * math.pi * freq * t) + 0.2 * math.sin(4 * math.pi * freq * t)
            chord_val += tone * env
        chord_val *= 0.12

        # Bass line (round sub bass)
        bass_env = math.exp(-pos_in_beat * 2.0)
        bass_val = math.sin(2 * math.pi * current_bass * t) * bass_env * 0.25

        left_samples[i] += chord_val + bass_val
        right_samples[i] += chord_val + bass_val

    # Drums: Kick on beats 0, 2.5; Snare on beats 1, 3; Hi-hat on every eighth note
    kick_times = []
    snare_times = []
    hat_times = []
    num_beats = int(DURATION / BEAT_SEC)

    for b in range(num_beats):
        b_time = b * BEAT_SEC
        if b % 4 in [0, 2]:
            kick_times.append(b_time)
        if b % 4 in [1, 3]:
            snare_times.append(b_time)
        hat_times.append(b_time)
        hat_times.append(b_time + EIGHTH_SEC)

    # Render Kick
    for kt in kick_times:
        start_sample = int(kt * SAMPLE_RATE)
        kick_duration = int(0.15 * SAMPLE_RATE)
        for j in range(kick_duration):
            idx = start_sample + j
            if idx < NUM_SAMPLES:
                frac = j / kick_duration
                freq = 130 * (1 - frac * 0.75)
                amp = math.exp(-frac * 8) * 0.5
                sample = math.sin(2 * math.pi * freq * (j / SAMPLE_RATE)) * amp
                left_samples[idx] += sample
                right_samples[idx] += sample

    # Render Snare
    for st in snare_times:
        start_sample = int(st * SAMPLE_RATE)
        snare_duration = int(0.12 * SAMPLE_RATE)
        for j in range(snare_duration):
            idx = start_sample + j
            if idx < NUM_SAMPLES:
                frac = j / snare_duration
                noise = (random.random() - 0.5) * 0.3
                body = math.sin(2 * math.pi * 180 * (j / SAMPLE_RATE)) * 0.2
                amp = math.exp(-frac * 12)
                sample = (noise + body) * amp
                left_samples[idx] += sample
                right_samples[idx] += sample

    # Render Hi-Hat
    for ht in hat_times:
        start_sample = int(ht * SAMPLE_RATE)
        hat_duration = int(0.04 * SAMPLE_RATE)
        for j in range(hat_duration):
            idx = start_sample + j
            if idx < NUM_SAMPLES:
                frac = j / hat_duration
                noise = (random.random() - 0.5) * 0.15
                amp = math.exp(-frac * 25)
                sample = noise * amp
                left_samples[idx] += sample * 0.7
                right_samples[idx] += sample * 0.9  # slight stereo pan

    # Normalize and write to WAV file
    max_amp = max(max(abs(s) for s in left_samples), max(abs(s) for s in right_samples), 1.0)
    scale = 28000.0 / max_amp

    with wave.open(filename, "wb") as wf:
        wf.setnchannels(2)
        wf.setsampwidth(2)
        wf.setframerate(SAMPLE_RATE)
        for i in range(NUM_SAMPLES):
            l = int(left_samples[i] * scale)
            r = int(right_samples[i] * scale)
            l = max(-32768, min(32767, l))
            r = max(-32768, min(32767, r))
            wf.writeframes(struct.pack("<hh", l, r))

    print(f"Generated upbeat lo-fi music track: {filename}")

if __name__ == "__main__":
    generate_lofi_track("/config/.gemini/antigravity/brain/1596fd6d-4215-4f92-9b21-1ac402f67dc6/upbeat_lofi.wav")
