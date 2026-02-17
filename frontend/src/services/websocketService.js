/**
 * WebSocket service for real-time game communication
 */

class WebSocketService {
  constructor() {
    this.ws = null;
    this.roomCode = null;
    this.token = null;
    this.listeners = new Map();
    this.reconnectAttempts = 0;
    this.maxReconnectAttempts = 5;
    this.reconnectDelay = 1000;
  }

  /**
   * Connect to game room WebSocket
   */
  connect(roomCode, token) {
    this.roomCode = roomCode;
    this.token = token;

    const wsUrl = `ws://localhost:8000/ws/game/${roomCode}?token=${token}`;

    this.ws = new WebSocket(wsUrl);

    this.ws.onopen = () => {
      console.log(`Connected to room ${roomCode}`);
      this.reconnectAttempts = 0;
      this.emit('connected', { roomCode });
    };

    this.ws.onmessage = (event) => {
      try {
        const message = JSON.parse(event.data);
        this.handleMessage(message);
      } catch (error) {
        console.error('Error parsing WebSocket message:', error);
      }
    };

    this.ws.onerror = (error) => {
      console.error('WebSocket error:', error);
      this.emit('error', error);
    };

    this.ws.onclose = () => {
      console.log('WebSocket closed');
      this.emit('disconnected');
      this.attemptReconnect();
    };
  }

  /**
   * Disconnect from WebSocket
   */
  disconnect() {
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
    this.roomCode = null;
    this.reconnectAttempts = this.maxReconnectAttempts; // Prevent reconnection
  }

  /**
   * Send message to server
   */
  send(type, data = {}) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      const message = { type, data };
      this.ws.send(JSON.stringify(message));
    } else {
      console.error('WebSocket is not connected');
    }
  }

  /**
   * Handle incoming messages
   */
  handleMessage(message) {
    const { type, data } = message;
    this.emit(type, data);
  }

  /**
   * Register event listener
   */
  on(eventType, callback) {
    if (!this.listeners.has(eventType)) {
      this.listeners.set(eventType, []);
    }
    this.listeners.get(eventType).push(callback);
  }

  /**
   * Remove event listener
   */
  off(eventType, callback) {
    if (this.listeners.has(eventType)) {
      const callbacks = this.listeners.get(eventType);
      const index = callbacks.indexOf(callback);
      if (index > -1) {
        callbacks.splice(index, 1);
      }
    }
  }

  /**
   * Emit event to listeners
   */
  emit(eventType, data) {
    if (this.listeners.has(eventType)) {
      this.listeners.get(eventType).forEach(callback => {
        try {
          callback(data);
        } catch (error) {
          console.error(`Error in ${eventType} listener:`, error);
        }
      });
    }
  }

  /**
   * Attempt to reconnect
   */
  attemptReconnect() {
    if (this.reconnectAttempts < this.maxReconnectAttempts && this.roomCode && this.token) {
      this.reconnectAttempts++;
      console.log(`Reconnecting... attempt ${this.reconnectAttempts}`);

      setTimeout(() => {
        this.connect(this.roomCode, this.token);
      }, this.reconnectDelay * this.reconnectAttempts);
    }
  }

  // Game-specific methods

  /**
   * Mark player as ready
   */
  markReady() {
    this.send('ready');
  }

  /**
   * Submit answer
   */
  submitAnswer(answerId, timeTaken) {
    this.send('answer', { answer_id: answerId, time_taken: timeTaken });
  }

  /**
   * Buzz in (Jeopardy mode)
   */
  buzz() {
    this.send('buzz', { timestamp: Date.now() });
  }

  /**
   * Send chat message
   */
  sendChat(message) {
    this.send('chat', { message });
  }

  /**
   * Start game (host only)
   */
  startGame() {
    this.send('start_game');
  }
}

// Export singleton instance
export default new WebSocketService();
