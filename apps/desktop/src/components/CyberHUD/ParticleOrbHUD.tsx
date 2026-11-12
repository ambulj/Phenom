import React, { useState, useEffect } from 'react';
import {
  Card,
  Text,
  Button,
  Slider,
  Badge,
  makeStyles,
  shorthands
} from '@fluentui/react-components';
import {
  MicRegular,
  MicOffRegular,
  FlashRegular,
  DismissRegular,
  SoundWaveCircleRegular,
  ShieldRegular
} from '@fluentui/react-icons';
import { ParticleOrb, OrbEmotion, FrequencyBands } from './ParticleOrb';

const useStyles = makeStyles({
  container: {
    display: 'flex',
    flexDirection: 'column',
    width: '540px',
    backgroundColor: 'rgba(10, 14, 23, 0.94)',
    backdropFilter: 'blur(16px)',
    border: '1px solid rgba(0, 229, 255, 0.28)',
    boxShadow: '0 8px 32px rgba(0, 0, 0, 0.65), 0 0 16px rgba(0, 229, 255, 0.15)',
    ...shorthands.borderRadius('12px'),
    ...shorthands.padding('16px'),
    color: '#e2e8f0',
    fontFamily: 'Segoe UI, sans-serif',
    zIndex: 1000
  },
  header: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: '12px',
    borderBottom: '1px solid rgba(255, 255, 255, 0.08)',
    paddingBottom: '8px'
  },
  titleGroup: {
    display: 'flex',
    alignItems: 'center',
    ...shorthands.gap('8px')
  },
  orbWrapper: {
    display: 'flex',
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: 'rgba(3, 7, 18, 0.65)',
    ...shorthands.borderRadius('8px'),
    ...shorthands.padding('8px'),
    marginBottom: '12px',
    position: 'relative'
  },
  metersRow: {
    display: 'grid',
    gridTemplateColumns: 'repeat(3, 1fr)',
    ...shorthands.gap('8px'),
    marginBottom: '12px'
  },
  meterCard: {
    backgroundColor: 'rgba(15, 23, 42, 0.6)',
    ...shorthands.padding('6px', '8px'),
    ...shorthands.borderRadius('6px'),
    display: 'flex',
    flexDirection: 'column',
    ...shorthands.gap('4px')
  },
  meterBarOuter: {
    width: '100%',
    height: '6px',
    backgroundColor: 'rgba(255, 255, 255, 0.1)',
    ...shorthands.borderRadius('3px'),
    overflow: 'hidden'
  },
  meterBarInner: {
    height: '100%',
    transition: 'width 0.08s ease-out'
  },
  controlsRow: {
    display: 'flex',
    flexDirection: 'column',
    ...shorthands.gap('10px'),
    marginBottom: '12px'
  },
  buttonRibbon: {
    display: 'flex',
    flexWrap: 'wrap',
    ...shorthands.gap('8px')
  },
  emotionBadgeGroup: {
    display: 'flex',
    ...shorthands.gap('6px'),
    marginTop: '6px'
  }
});

interface ParticleOrbHUDProps {
  onClose?: () => void;
  onSendIntent?: (intent: string) => void;
}

export const ParticleOrbHUD: React.FC<ParticleOrbHUDProps> = ({ onClose, onSendIntent }) => {
  const styles = useStyles();

  const [emotion, setEmotion] = useState<OrbEmotion>('idle');
  const [sensitivity, setSensitivity] = useState<number>(0.65);
  const [isMuted, setIsMuted] = useState<boolean>(false);
  const [isHalted, setIsHalted] = useState<boolean>(false);
  const [simulatedVolume, setSimulatedVolume] = useState<number>(0.25);
  const [freqBands, setFreqBands] = useState<FrequencyBands>({
    bass: 0.15,
    mid: 0.2,
    treble: 0.1,
    overall: 0.2
  });

  // Dynamic audio frequency simulator for reactive demo / visual verification
  useEffect(() => {
    let animId: number;
    let t = 0;

    const tick = () => {
      animId = requestAnimationFrame(tick);
      t += 0.05;

      if (isMuted || isHalted) {
        setFreqBands({ bass: 0, mid: 0, treble: 0, overall: 0 });
        return;
      }

      const vol = simulatedVolume;
      const b = (Math.sin(t * 2.5) * 0.5 + 0.5) * vol * 1.2;
      const m = (Math.sin(t * 4.0 + 1.0) * 0.5 + 0.5) * vol * 1.4;
      const tr = (Math.sin(t * 7.0 + 2.0) * 0.5 + 0.5) * vol * 1.6;
      const ov = (b + m + tr) / 3.0;

      setFreqBands({
        bass: Math.min(1.0, b),
        mid: Math.min(1.0, m),
        treble: Math.min(1.0, tr),
        overall: Math.min(1.0, ov)
      });
    };

    tick();
    return () => cancelAnimationFrame(animId);
  }, [simulatedVolume, isMuted, isHalted]);

  const handleSensitivityChange = (_: any, data: { value: number }) => {
    setSensitivity(data.value);
    onSendIntent?.(`set wake word sensitivity to ${data.value.toFixed(2)}`);
  };

  const handleToggleMute = () => {
    const nextMute = !isMuted;
    setIsMuted(nextMute);
    onSendIntent?.(nextMute ? 'mute microphone' : 'unmute microphone');
  };

  const handleManualWake = () => {
    onSendIntent?.('trigger wake word');
    setEmotion('speaking');
    setTimeout(() => {
      if (!isHalted) setEmotion('idle');
    }, 3500);
  };

  const handleSetEmotion = (em: OrbEmotion) => {
    setEmotion(em);
    onSendIntent?.(`set orb emotion to ${em}`);
  };

  const handleEmergencySilence = () => {
    setIsHalted(!isHalted);
    if (!isHalted) {
      setEmotion('halted');
      setIsMuted(true);
    } else {
      setEmotion('idle');
      setIsMuted(false);
    }
  };

  return (
    <Card className={styles.container}>
      {/* Header */}
      <div className={styles.header}>
        <div className={styles.titleGroup}>
          <SoundWaveCircleRegular style={{ color: '#00E5FF', fontSize: '20px' }} />
          <div>
            <Text weight="semibold" style={{ color: '#00E5FF', fontSize: '14px' }}>
              REACTIVE 3D PARTICLE ORB & WAKE-WORD HUD
            </Text>
            <Text size={100} style={{ color: '#94a3b8', display: 'block' }}>
              VOX-04.1 • VOX-04.2 • ORB-02.1 • Three.js WebGL FFT • Local ONNX
            </Text>
          </div>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Badge
            appearance="filled"
            style={{
              backgroundColor: isHalted ? '#EF4444' : isMuted ? '#F59E0B' : '#10B981',
              color: '#000'
            }}
          >
            {isHalted ? 'HALTED (<10ms)' : isMuted ? 'MIC MUTED' : 'LISTENING'}
          </Badge>
          {onClose && (
            <Button
              appearance="subtle"
              icon={<DismissRegular />}
              size="small"
              onClick={onClose}
            />
          )}
        </div>
      </div>

      {/* Orb Viewport */}
      <div className={styles.orbWrapper}>
        <ParticleOrb
          emotion={isHalted ? 'halted' : emotion}
          frequencyBands={freqBands}
          qualityLevel="high"
          isHalted={isHalted}
          width={490}
          height={260}
        />
      </div>

      {/* Frequency Spectrum Meters */}
      <div className={styles.metersRow}>
        <div className={styles.meterCard}>
          <div style={{ display: 'flex', justifyContent: 'space-between' }}>
            <Text size={100} style={{ color: '#94a3b8' }}>BASS (Dilation)</Text>
            <Text size={100} style={{ color: '#00E5FF' }}>{(freqBands.bass * 100).toFixed(0)}%</Text>
          </div>
          <div className={styles.meterBarOuter}>
            <div
              className={styles.meterBarInner}
              style={{ width: `${freqBands.bass * 100}%`, backgroundColor: '#00E5FF' }}
            />
          </div>
        </div>

        <div className={styles.meterCard}>
          <div style={{ display: 'flex', justifyContent: 'space-between' }}>
            <Text size={100} style={{ color: '#94a3b8' }}>MID (Turbulence)</Text>
            <Text size={100} style={{ color: '#A855F7' }}>{(freqBands.mid * 100).toFixed(0)}%</Text>
          </div>
          <div className={styles.meterBarOuter}>
            <div
              className={styles.meterBarInner}
              style={{ width: `${freqBands.mid * 100}%`, backgroundColor: '#A855F7' }}
            />
          </div>
        </div>

        <div className={styles.meterCard}>
          <div style={{ display: 'flex', justifyContent: 'space-between' }}>
            <Text size={100} style={{ color: '#94a3b8' }}>TREBLE (Glitter)</Text>
            <Text size={100} style={{ color: '#FFB300' }}>{(freqBands.treble * 100).toFixed(0)}%</Text>
          </div>
          <div className={styles.meterBarOuter}>
            <div
              className={styles.meterBarInner}
              style={{ width: `${freqBands.treble * 100}%`, backgroundColor: '#FFB300' }}
            />
          </div>
        </div>
      </div>

      {/* Controls & Ribbon */}
      <div className={styles.controlsRow}>
        <div>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px' }}>
            <Text size={200} weight="semibold">Detection Sensitivity: {(sensitivity * 100).toFixed(0)}%</Text>
            <Text size={100} style={{ color: '#94a3b8' }}>Keyword: "Hey Phenom" / "Phenom"</Text>
          </div>
          <Slider
            min={0.1}
            max={1.0}
            step={0.05}
            value={sensitivity}
            onChange={handleSensitivityChange}
          />
        </div>

        <div>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px' }}>
            <Text size={200} weight="semibold">Frequency Modulation Energy</Text>
            <Text size={100} style={{ color: '#00E5FF' }}>{(simulatedVolume * 100).toFixed(0)}%</Text>
          </div>
          <Slider
            min={0.0}
            max={1.0}
            step={0.05}
            value={simulatedVolume}
            onChange={(_, d) => setSimulatedVolume(d.value)}
          />
        </div>

        {/* Emotion Preset Badges */}
        <div>
          <Text size={200} weight="semibold" style={{ display: 'block', marginBottom: '4px' }}>
            Orb Emotional Theme:
          </Text>
          <div className={styles.emotionBadgeGroup}>
            {(['urgent', 'focused', 'chill', 'idle', 'speaking'] as OrbEmotion[]).map((em) => (
              <Button
                key={em}
                size="small"
                appearance={emotion === em ? 'primary' : 'outline'}
                onClick={() => handleSetEmotion(em)}
                style={{ textTransform: 'capitalize', fontSize: '11px' }}
              >
                {em}
              </Button>
            ))}
          </div>
        </div>
      </div>

      {/* Action Buttons */}
      <div className={styles.buttonRibbon}>
        <Button
          appearance={isMuted ? 'subtle' : 'secondary'}
          icon={isMuted ? <MicOffRegular /> : <MicRegular />}
          onClick={handleToggleMute}
          size="small"
        >
          {isMuted ? 'Unmute Mic' : 'Mute Mic'}
        </Button>

        <Button
          appearance="primary"
          icon={<FlashRegular />}
          onClick={handleManualWake}
          size="small"
        >
          Manual Wake ("Hey Phenom")
        </Button>

        <Button
          appearance="subtle"
          icon={<ShieldRegular style={{ color: isHalted ? '#10B981' : '#EF4444' }} />}
          onClick={handleEmergencySilence}
          size="small"
          style={{ marginLeft: 'auto', color: isHalted ? '#10B981' : '#EF4444' }}
        >
          {isHalted ? 'Resume Audio' : 'Guardian Audio Silence (<10ms)'}
        </Button>
      </div>
    </Card>
  );
};
