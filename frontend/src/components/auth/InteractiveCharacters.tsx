import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';

interface InteractiveCharactersProps {
  focusedField: 'email' | 'password' | null;
  isTyping?: boolean;
  showPassword?: boolean;
  isSuccess?: boolean;
}

export const InteractiveCharacters: React.FC<InteractiveCharactersProps> = ({
  focusedField,
  isTyping = false,
  showPassword = false,
  isSuccess = false,
}) => {
  const [mousePos, setMousePos] = useState({ x: 0, y: 0 });
  const [isBlinking, setIsBlinking] = useState(false);

  // Smooth mouse tracking with window listener
  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      // Normalize -1 to 1
      const x = (e.clientX / window.innerWidth) * 2 - 1;
      const y = (e.clientY / window.innerHeight) * 2 - 1;
      setMousePos({ x, y });
    };

    window.addEventListener('mousemove', handleMouseMove);
    return () => window.removeEventListener('mousemove', handleMouseMove);
  }, []);

  // Periodic natural blinking
  useEffect(() => {
    const blinkInterval = setInterval(() => {
      setIsBlinking(true);
      setTimeout(() => setIsBlinking(false), 150);
    }, 4200);
    return () => clearInterval(blinkInterval);
  }, []);

  // Dynamic state checks
  const isCoveringEyes = focusedField === 'password' && !showPassword;
  const isPeeking = focusedField === 'password' && showPassword;
  const isLookingAtForm = focusedField === 'email';

  // Base eye pupil offsets
  let pupilX = mousePos.x * 6;
  let pupilY = mousePos.y * 5;

  if (isLookingAtForm) {
    pupilX = 9; // Look rightwards directly into input
    pupilY = 3;
  } else if (isCoveringEyes) {
    pupilX = 0;
    pupilY = -2;
  } else if (isPeeking) {
    pupilX = 7;
    pupilY = 1;
  }

  return (
    <div className="relative w-full h-[440px] flex items-center justify-center select-none overflow-visible">
      {/* Ambient floating elements with subtle parallax */}
      <motion.div
        animate={{
          x: mousePos.x * -15,
          y: mousePos.y * -15 + [0, -6, 0][0],
        }}
        transition={{ type: 'spring', damping: 25, stiffness: 60 }}
        className="absolute top-8 left-12 w-3 h-3 rounded-full bg-purple-400/30 blur-[1px] pointer-events-none"
      />
      <motion.div
        animate={{
          x: mousePos.x * 12,
          y: mousePos.y * 12,
        }}
        transition={{ type: 'spring', damping: 25, stiffness: 60 }}
        className="absolute bottom-16 right-10 w-4 h-4 rounded-full bg-amber-400/40 blur-[1px] pointer-events-none"
      />
      <motion.div
        animate={{
          x: mousePos.x * -8,
          y: mousePos.y * -8,
        }}
        transition={{ type: 'spring', damping: 25, stiffness: 60 }}
        className="absolute top-20 right-16 text-slate-400/40 font-mono text-sm pointer-events-none select-none"
      >
        ✦
      </motion.div>

      <svg
        viewBox="0 0 520 440"
        className="w-full h-full max-w-[480px] overflow-visible"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
      >
        {/* Soft ground shadow that reacts to character jumps */}
        <motion.ellipse
          animate={
            isSuccess
              ? { rx: [190, 150, 190], opacity: [0.08, 0.03, 0.08], transition: { repeat: Infinity, duration: 0.6 } }
              : { rx: 190, opacity: 0.07 }
          }
          cx="260"
          cy="420"
          rx="190"
          ry="14"
          fill="#000000"
        />

        {/* ========================================================= */}
        {/* 1. TALL PURPLE CHARACTER (Back-Left Tilted Geometric Body) */}
        {/* ========================================================= */}
        <motion.g
          animate={
            isSuccess
              ? {
                  y: [-30, 0],
                  scaleY: [1.08, 0.95, 1],
                  rotate: [-3, 3, 0],
                  transition: { repeat: Infinity, duration: 0.5, ease: 'easeInOut' },
                }
              : isLookingAtForm
              ? {
                  rotate: 6 + (isTyping ? 1.5 : 0),
                  x: 18 + (isTyping ? 3 : 0),
                  y: isTyping ? -3 : 0,
                  skewX: -2,
                }
              : isCoveringEyes
              ? {
                  rotate: -4,
                  y: 12,
                  scaleY: 0.96,
                }
              : isPeeking
              ? {
                  rotate: 3,
                  y: -2,
                  scaleY: 1.02,
                }
              : {
                  // Idle subtle breathing & mouse parallax tilt
                  rotate: mousePos.x * 5,
                  x: mousePos.x * 8,
                  y: mousePos.y * 5,
                  scaleY: [1, 1.015, 1],
                  transition: { duration: 3.5, repeat: Infinity, ease: 'easeInOut' },
                }
          }
          transition={{ type: 'spring', stiffness: 180, damping: 20 }}
          style={{ originX: '170px', originY: '410px' }}
        >
          {/* Main Inverted Trapezoid Body */}
          <path
            d="M120 145 C120 138, 126 132, 134 132 L226 132 C234 132, 240 138, 238 146 L210 410 L135 410 Z"
            fill="#5F2EEA"
          />

          {/* Facial Features */}
          <g transform="translate(168, 180)">
            {/* Left Eye */}
            <circle cx="0" cy="0" r="5" fill="#FFFFFF" />
            <motion.circle
              animate={{ cx: pupilX * 0.9, cy: pupilY * 0.9 }}
              transition={{ type: 'spring', stiffness: 350, damping: 26 }}
              r={isBlinking ? '0.6' : '3'}
              fill="#111827"
            />
            {/* Right Eye */}
            <circle cx="26" cy="0" r="5" fill="#FFFFFF" />
            <motion.circle
              animate={{ cx: 26 + pupilX * 0.9, cy: pupilY * 0.9 }}
              transition={{ type: 'spring', stiffness: 350, damping: 26 }}
              r={isBlinking ? '0.6' : '3'}
              fill="#111827"
            />
            {/* Expressive Mouth */}
            <motion.path
              animate={
                isSuccess
                  ? { d: 'M6 14 Q13 24 20 14' }
                  : isLookingAtForm
                  ? { d: 'M8 16 Q13 19 18 16' }
                  : isCoveringEyes
                  ? { d: 'M6 20 Q13 14 20 20' }
                  : { d: 'M7 18 Q13 15 19 18' }
              }
              fill="none"
              stroke="#111827"
              strokeWidth="3.5"
              strokeLinecap="round"
            />
          </g>

          {/* Full-Body Animated Arms & Paws covering eyes */}
          <motion.g
            animate={
              isSuccess
                ? { y: -90, rotate: [0, 15, -15, 0], opacity: 1, transition: { repeat: Infinity, duration: 0.5 } }
                : isCoveringEyes
                ? { y: 0, opacity: 1, scale: 1 }
                : isPeeking
                ? { y: 16, opacity: 0.9, scale: 0.95 }
                : { y: 80, opacity: 0, scale: 0.8 }
            }
            transition={{ type: 'spring', stiffness: 220, damping: 22 }}
          >
            {/* Left Hand Arm */}
            <path
              d="M125 240 Q145 195 162 182"
              stroke="#4B20B8"
              strokeWidth="16"
              strokeLinecap="round"
              fill="none"
            />
            {/* Right Hand Arm */}
            <path
              d="M230 240 Q210 195 198 182"
              stroke="#4B20B8"
              strokeWidth="16"
              strokeLinecap="round"
              fill="none"
            />
          </motion.g>
        </motion.g>

        {/* ========================================================= */}
        {/* 2. BLACK CHARACTER (Center Tall Pillar)                   */}
        {/* ========================================================= */}
        <motion.g
          animate={
            isSuccess
              ? {
                  y: [-38, 0],
                  scaleY: [1.1, 0.95, 1],
                  transition: { repeat: Infinity, duration: 0.48, delay: 0.05, ease: 'easeInOut' },
                }
              : isLookingAtForm
              ? {
                  x: 14 + (isTyping ? 2 : 0),
                  y: isTyping ? -4 : -2,
                  scaleY: 1.03,
                  rotate: 2,
                }
              : isCoveringEyes
              ? {
                  y: 18,
                  scaleY: 0.92,
                  rotate: -1,
                }
              : isPeeking
              ? {
                  y: -6,
                  scaleY: 1.05,
                  rotate: 1,
                }
              : {
                  // Subtle vertical breathe & mouse tracking
                  x: mousePos.x * 12,
                  y: mousePos.y * 8,
                  scaleY: [1, 0.985, 1],
                  transition: { duration: 4.2, repeat: Infinity, ease: 'easeInOut' },
                }
          }
          transition={{ type: 'spring', stiffness: 200, damping: 20 }}
          style={{ originX: '235px', originY: '410px' }}
        >
          {/* Tall Charcoal Pillar Body */}
          <rect x="200" y="220" width="70" height="190" rx="10" fill="#1C1D24" />

          {/* Big White Inset Eyes */}
          <g transform="translate(222, 246)">
            {/* Left Eye */}
            <circle cx="0" cy="0" r="8" fill="#FFFFFF" />
            <motion.circle
              animate={{
                cx: isCoveringEyes ? 0 : pupilX * 1.1,
                cy: isCoveringEyes ? 0 : pupilY * 1.1,
              }}
              transition={{ type: 'spring', stiffness: 380, damping: 28 }}
              r={isBlinking ? '1' : '4'}
              fill="#1C1D24"
            />
            {/* Right Eye */}
            <circle cx="24" cy="0" r="8" fill="#FFFFFF" />
            <motion.circle
              animate={{
                cx: 24 + (isCoveringEyes ? 0 : pupilX * 1.1),
                cy: isCoveringEyes ? 0 : pupilY * 1.1,
              }}
              transition={{ type: 'spring', stiffness: 380, damping: 28 }}
              r={isBlinking ? '1' : '4'}
              fill="#1C1D24"
            />
          </g>

          {/* Hands covering eyes */}
          <motion.g
            animate={
              isSuccess
                ? { y: -80, opacity: 1 }
                : isCoveringEyes
                ? { y: 0, opacity: 1 }
                : isPeeking
                ? { y: 18, opacity: 0.9 }
                : { y: 60, opacity: 0 }
            }
            transition={{ type: 'spring', stiffness: 240, damping: 22 }}
          >
            <circle cx="218" cy="248" r="12" fill="#2E303C" />
            <circle cx="248" cy="248" r="12" fill="#2E303C" />
          </motion.g>
        </motion.g>

        {/* ========================================================= */}
        {/* 3. ORANGE DOME CHARACTER (Front-Left Huge Wide Half-Dome)  */}
        {/* ========================================================= */}
        <motion.g
          animate={
            isSuccess
              ? {
                  y: [-22, 0],
                  scaleX: [1, 1.05, 1],
                  scaleY: [1, 0.94, 1],
                  transition: { repeat: Infinity, duration: 0.42, delay: 0.1 },
                }
              : isLookingAtForm
              ? {
                  x: 10,
                  rotate: 2,
                  scaleY: 1.02,
                }
              : isCoveringEyes
              ? {
                  scaleY: 0.88,
                  y: 18,
                  rotate: -1,
                }
              : isPeeking
              ? {
                  scaleY: 1.04,
                  y: -4,
                }
              : {
                  // Body breathing cycle
                  x: mousePos.x * 14,
                  y: mousePos.y * 7,
                  scaleY: [1, 0.97, 1],
                  transition: { duration: 3.8, repeat: Infinity, ease: 'easeInOut' },
                }
          }
          transition={{ type: 'spring', stiffness: 220, damping: 20 }}
          style={{ originX: '150px', originY: '410px' }}
        >
          {/* Half-Dome Organic Curve */}
          <path
            d="M60 410 C60 280, 245 280, 245 410 Z"
            fill="#FF7A30"
          />

          {/* Minimal Face */}
          <g transform="translate(170, 335)">
            {/* Left Eye */}
            <motion.circle
              animate={{
                cx: -14 + (isCoveringEyes ? 0 : pupilX * 0.8),
                cy: isCoveringEyes ? 0 : pupilY * 0.8,
              }}
              r={isBlinking ? 1 : 3}
              fill="#111827"
            />
            {/* Right Eye */}
            <motion.circle
              animate={{
                cx: 14 + (isCoveringEyes ? 0 : pupilX * 0.8),
                cy: isCoveringEyes ? 0 : pupilY * 0.8,
              }}
              r={isBlinking ? 1 : 3}
              fill="#111827"
            />
            {/* Small Mouth */}
            <motion.path
              animate={
                isSuccess
                  ? { d: 'M-5 12 Q0 18 5 12' }
                  : isCoveringEyes
                  ? { d: 'M-4 15 Q0 11 4 15' }
                  : { d: 'M-4 13 Q0 16 4 13' }
              }
              fill="none"
              stroke="#111827"
              strokeWidth="3"
              strokeLinecap="round"
            />
          </g>

          {/* Orange paws covering eyes */}
          <motion.g
            animate={
              isSuccess
                ? { y: -50, opacity: 1 }
                : isCoveringEyes
                ? { y: 0, opacity: 1 }
                : isPeeking
                ? { y: 16, opacity: 0.9 }
                : { y: 40, opacity: 0 }
            }
            transition={{ type: 'spring', stiffness: 260, damping: 22 }}
          >
            <circle cx="150" cy="336" r="10" fill="#E65D14" />
            <circle cx="188" cy="336" r="10" fill="#E65D14" />
          </motion.g>
        </motion.g>

        {/* ========================================================= */}
        {/* 4. YELLOW CHARACTER (Front-Right Pill with Sideways Mouth) */}
        {/* ========================================================= */}
        <motion.g
          animate={
            isSuccess
              ? {
                  y: [-32, 0],
                  rotate: [0, 6, -6, 0],
                  transition: { repeat: Infinity, duration: 0.45, delay: 0.08 },
                }
              : isLookingAtForm
              ? {
                  x: 14,
                  rotate: 5,
                  scaleY: 1.02,
                }
              : isCoveringEyes
              ? {
                  rotate: 15,
                  scaleX: -0.9, // Turns body away!
                  x: 8,
                  y: 12,
                }
              : isPeeking
              ? {
                  rotate: -3,
                  scaleX: 1.05,
                  x: -6, // Leans towards center to peek!
                  y: -6,
                }
              : {
                  // Natural body sway & mouse tracking
                  x: mousePos.x * 16,
                  y: mousePos.y * 9,
                  rotate: mousePos.x * 3,
                  scaleY: [1, 1.02, 1],
                  transition: { duration: 4.0, repeat: Infinity, ease: 'easeInOut' },
                }
          }
          transition={{ type: 'spring', stiffness: 220, damping: 20 }}
          style={{ originX: '280px', originY: '410px' }}
        >
          {/* Curved Pill Body */}
          <path
            d="M245 410 L250 310 C254 265, 320 265, 324 310 L320 410 Z"
            fill="#F9D638"
          />

          {/* Minimal Face */}
          <g transform="translate(294, 298)">
            {/* Eye */}
            <motion.circle
              animate={{
                cx: isCoveringEyes ? 0 : pupilX * 0.9,
                cy: isCoveringEyes ? 0 : pupilY * 0.9,
              }}
              r={isBlinking ? 0.8 : 3.5}
              fill="#111827"
            />
            {/* Characteristic Outcrowd Sideways Squiggle Mouth */}
            <path
              d="M-2 12 Q6 8 16 12"
              fill="none"
              stroke="#111827"
              strokeWidth="3.5"
              strokeLinecap="round"
            />
          </g>

          {/* Yellow Hand covering face */}
          <motion.g
            animate={
              isSuccess
                ? { y: -60, opacity: 1 }
                : isCoveringEyes
                ? { y: 0, opacity: 1 }
                : isPeeking
                ? { y: 14, opacity: 0.9 }
                : { y: 40, opacity: 0 }
            }
            transition={{ type: 'spring', stiffness: 250, damping: 22 }}
          >
            <circle cx="292" cy="300" r="11" fill="#E5C227" />
          </motion.g>
        </motion.g>
      </svg>
    </div>
  );
};
