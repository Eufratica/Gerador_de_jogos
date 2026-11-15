# AUDIO_PIPELINE.md — Pipeline de Áudio

## 1. Estado Real Atual (Fase 0)

O jogo-âncora (`Zaikor`) utiliza síntese procedural nativa em GDScript em [procedural_sfx.gd](file:///C:/Jogo_Android/src/engine/audio/procedural_sfx.gd):
- **16 efeitos sonoros sintéticos `AudioStreamWAV`** (16-bit mono, `22050 Hz`), pré-gerados em memória no `_ready()` e disparados via pool circular de `8` `AudioStreamPlayer` (desabilitado automaticamente em driver `headless`).
- Atualmente **não há trilha sonora nem arquivos `.wav`/`.ogg` externos** no repositório.

---

## 2. Evolução Prevista (Fase 7)

1. Preservar o módulo de síntese procedural como gerador leve de SFX base para templates sem assets externos.
2. Integrar ferramentas gratuitas locais (`Audacity`, `FFmpeg`, síntese local) para normalização, corte de silêncio/fade e compressão `.ogg`/`.wav` otimizada.
3. Aplicar os mesmos controles do `Asset Registry` (procedência, licença comercial compatível, hash e detecção de clipe/volume) antes de integrar música ou voz em um jogo gerado.
