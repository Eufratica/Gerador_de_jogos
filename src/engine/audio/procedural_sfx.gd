class_name ProceduralSfx
extends Node
## Sintetizador procedural leve de SFX em memoria (pre-gerado no _ready, Zero GC no gameplay).

const SAMPLE_RATE: int = 22050
const POOL_SIZE: int = 8

var _streams: Dictionary = {}
var _players: Array[AudioStreamPlayer] = []
var _cursor: int = 0
var _enabled: bool = true


func _ready() -> void:
	_enabled = DisplayServer.get_name() != "headless"
	for _i in range(POOL_SIZE):
		var p := AudioStreamPlayer.new()
		p.volume_db = -8.0
		add_child(p)
		_players.append(p)
	_bake_all_streams()


func set_enabled(on: bool) -> void:
	_enabled = on and DisplayServer.get_name() != "headless"


func play(sfx_id: String, pitch: float = 1.0) -> void:
	if not _enabled or not _streams.has(sfx_id):
		return
	var p: AudioStreamPlayer = _players[_cursor]
	_cursor = (_cursor + 1) % POOL_SIZE
	p.stop()
	p.stream = _streams[sfx_id]
	p.pitch_scale = pitch
	p.play()


func _bake_all_streams() -> void:
	_streams["slash_1"] = _make_sweep(0.11, 520.0, 140.0, 0.35, 0.35)
	_streams["slash_2"] = _make_sweep(0.13, 640.0, 160.0, 0.40, 0.38)
	_streams["slash_3"] = _make_sweep(0.19, 380.0, 85.0, 0.50, 0.48)
	_streams["dash"] = _make_sweep(0.14, 780.0, 220.0, 0.45, 0.28)
	_streams["fire"] = _make_sweep(0.32, 260.0, 75.0, 0.70, 0.42)
	_streams["ice"] = _make_sweep(0.28, 1250.0, 520.0, 0.45, 0.34)
	_streams["lightning"] = _make_sweep(0.24, 1600.0, 190.0, 0.65, 0.42)
	_streams["aegis"] = _make_sweep(0.30, 180.0, 460.0, 0.15, 0.44)
	_streams["hit"] = _make_sweep(0.08, 220.0, 65.0, 0.50, 0.32)
	_streams["dodge"] = _make_sweep(0.12, 540.0, 960.0, 0.10, 0.28)
	_streams["altar"] = _make_chime(0.45, PackedFloat64Array([330.0, 440.0, 659.25]), 0.35)
	_streams["chest"] = _make_chime(0.32, PackedFloat64Array([523.25, 659.25, 783.99]), 0.32)
	_streams["portal"] = _make_sweep(0.35, 240.0, 680.0, 0.25, 0.34)
	_streams["qte"] = _make_sweep(0.38, 420.0, 70.0, 0.55, 0.55)
	_streams["rage"] = _make_sweep(0.42, 130.0, 390.0, 0.40, 0.48)
	_streams["ui"] = _make_chime(0.07, PackedFloat64Array([680.0]), 0.20)


func _make_sweep(dur_s: float, f_start: float, f_end: float, noise_mix: float, gain: float) -> AudioStreamWAV:
	var n: int = int(dur_s * float(SAMPLE_RATE))
	var pcm := PackedByteArray()
	pcm.resize(n * 2)
	var phase: float = 0.0
	var seed_i: int = 1337
	for i in range(n):
		var t: float = float(i) / float(maxi(1, n - 1))
		var freq: float = lerpf(f_start, f_end, t)
		phase += (TAU * freq) / float(SAMPLE_RATE)
		seed_i = (seed_i * 1103515245 + 12345) & 0x7FFFFFFF
		var noise: float = (float(seed_i) / 1073741824.0) - 1.0
		var env: float = (1.0 - t) * (1.0 - t)
		var sig: float = ((sin(phase) * (1.0 - noise_mix)) + (noise * noise_mix)) * env * gain
		pcm.encode_s16(i * 2, clampi(int(sig * 32767.0), -32767, 32767))
	return _wrap_wav(pcm)


func _make_chime(dur_s: float, freqs: PackedFloat64Array, gain: float) -> AudioStreamWAV:
	var n: int = int(dur_s * float(SAMPLE_RATE))
	var pcm := PackedByteArray()
	pcm.resize(n * 2)
	for i in range(n):
		var t: float = float(i) / float(maxi(1, n - 1))
		var sec: float = t * dur_s
		var acc: float = 0.0
		for f in freqs:
			acc += sin(TAU * f * sec)
		acc /= float(maxi(1, freqs.size()))
		var env: float = pow(1.0 - t, 1.5)
		pcm.encode_s16(i * 2, clampi(int(acc * env * gain * 32767.0), -32767, 32767))
	return _wrap_wav(pcm)


func _wrap_wav(pcm: PackedByteArray) -> AudioStreamWAV:
	var wav := AudioStreamWAV.new()
	wav.format = AudioStreamWAV.FORMAT_16_BITS
	wav.mix_rate = SAMPLE_RATE
	wav.stereo = false
	wav.data = pcm
	return wav
