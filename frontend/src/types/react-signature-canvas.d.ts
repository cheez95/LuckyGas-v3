declare module 'react-signature-canvas' {
  import { Component } from 'react';

  export interface SignatureCanvasProps {
    velocityFilterWeight?: number;
    minWidth?: number;
    maxWidth?: number;
    minDistance?: number;
    dotSize?: number | (() => number);
    penColor?: string;
    throttle?: number;
    onEnd?: (event: MouseEvent | TouchEvent) => void;
    onBegin?: (event: MouseEvent | TouchEvent) => void;
    canvasProps?: React.CanvasHTMLAttributes<HTMLCanvasElement>;
    clearOnResize?: boolean;
  }

  export default class SignatureCanvas extends Component<SignatureCanvasProps> {
    clear(): void;
    fromDataURL(dataURL: string, options?: { ratio?: number; width?: number; height?: number }): void;
    toDataURL(type?: string, encoderOptions?: number): string;
    fromData(pointGroups: Array<{ x: number; y: number; time: number }[]>): void;
    toData(): Array<{ x: number; y: number; time: number }[]>;
    isEmpty(): boolean;
    getTrimmedCanvas(): HTMLCanvasElement;
    getCanvas(): HTMLCanvasElement;
  }
}