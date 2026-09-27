import type { ReactNode } from 'react';
import type { InteractionState } from '../types';
import { InteractionOutline } from './InteractionOutline';

export type SelectableGroupProps = {
  position?: [number, number, number];
  interaction?: InteractionState;
  onClick?: () => void;
  onPointerOver?: () => void;
  onPointerOut?: () => void;
  outline?: boolean;
  children: ReactNode;
};

export function SelectableGroup({
  position = [0, 0, 0],
  interaction = 'idle',
  onClick,
  onPointerOver,
  onPointerOut,
  outline = true,
  children,
}: SelectableGroupProps) {
  return (
    <group
      position={position}
      onClick={(e) => {
        e.stopPropagation();
        onClick?.();
      }}
      onPointerOver={(e) => {
        e.stopPropagation();
        onPointerOver?.();
      }}
      onPointerOut={(e) => {
        e.stopPropagation();
        onPointerOut?.();
      }}
    >
      {children}
      {outline && <InteractionOutline state={interaction} />}
    </group>
  );
}
