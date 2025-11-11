import { Server } from 'socket.io';

let ioInstance: Server | null = null;

export function registerSocketServer(io: Server) {
  ioInstance = io;
}

export function getIO(): Server {
  if (!ioInstance) {
    throw new Error('Socket.io instance not registered yet');
  }
  return ioInstance;
}

export function safeEmit(event: string, payload: any) {
  try {
    if (ioInstance) {
      ioInstance.emit(event, payload);
    }
  } catch (err) {
    console.error('safeEmit error', event, err);
  }
}
