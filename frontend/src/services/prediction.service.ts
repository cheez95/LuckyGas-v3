import api from './api';

export interface PredictionQuantities {
  '50kg': number;
  '20kg': number;
  '16kg': number;
  '10kg': number;
  '4kg': number;
}

export interface Prediction {
  id: number;
  customer_id: number;
  predicted_date: string;
  quantities: PredictionQuantities;
  confidence_score: number;
  model_version?: string;
  is_converted_to_order: boolean;
  created_at: string;
}

export interface CustomerPrediction {
  customer_id: number;
  predicted_date: string;
  quantities: PredictionQuantities;
  confidence_score: number;
  model_version?: string;
  created_at: string;
}

export interface PredictionBatchResponse {
  batch_id: string;
  predictions_count: number;
  model_version: string;
  execution_time_seconds: number;
  timestamp: string;
  summary: {
    urgent_deliveries: number;
    total_50kg: number;
    total_20kg: number;
    average_confidence: number;
  };
}

export interface PredictionMetrics {
  model_id: string;
  accuracy_metrics: {
    mae: number;
    rmse: number;
    mape: number;
  };
  feature_importance: {
    [key: string]: number;
  };
  last_training_date: string;
  predictions_generated_today: number;
  model_status: string;
}

export interface TrainingResponse {
  model_id: string;
  model_name: string;
  status: string;
  accuracy: number;
  created_at: string;
  training_hours: number;
  features_used: string[];
}

class PredictionService {
  // Train or retrain the model
  async trainModel(): Promise<TrainingResponse> {
    const response = await api.post('/predictions/train');
    return response.data;
  }

  // Generate batch predictions
  async generateBatchPredictions(): Promise<PredictionBatchResponse> {
    const response = await api.post('/predictions/batch');
    return response.data;
  }

  // Get predictions with filters
  async getPredictions(params?: {
    skip?: number;
    limit?: number;
    customer_id?: number;
    start_date?: string;
    end_date?: string;
    confidence_threshold?: number;
  }): Promise<Prediction[]> {
    const response = await api.get('/predictions', { params });
    return response.data;
  }

  // Get customer-specific prediction
  async getCustomerPrediction(customerId: number): Promise<CustomerPrediction> {
    const response = await api.get(`/predictions/customers/${customerId}`);
    return response.data;
  }

  // Get prediction metrics
  async getMetrics(): Promise<PredictionMetrics> {
    const response = await api.get('/predictions/metrics');
    return response.data;
  }

  // Convert prediction to order
  async convertToOrder(predictionId: number): Promise<{ message: string; prediction_id: number }> {
    const response = await api.post(`/predictions/${predictionId}/convert-to-order`);
    return response.data;
  }

  // Get urgent predictions (next 3 days)
  async getUrgentPredictions(): Promise<Prediction[]> {
    const today = new Date();
    const threeDaysLater = new Date(today);
    threeDaysLater.setDate(today.getDate() + 3);

    return this.getPredictions({
      start_date: today.toISOString().split('T')[0],
      end_date: threeDaysLater.toISOString().split('T')[0],
      confidence_threshold: 0.7,
    });
  }

  // Get prediction summary for dashboard
  async getPredictionSummary(): Promise<{
    total: number;
    urgent: number;
    converted: number;
    average_confidence: number;
  }> {
    const predictions = await this.getPredictions({ limit: 1000 });
    const today = new Date();
    const threeDaysLater = new Date(today);
    threeDaysLater.setDate(today.getDate() + 3);

    const urgent = predictions.filter(p => {
      const predDate = new Date(p.predicted_date);
      return predDate >= today && predDate <= threeDaysLater;
    });

    const converted = predictions.filter(p => p.is_converted_to_order);

    const avgConfidence = predictions.length > 0
      ? predictions.reduce((sum, p) => sum + p.confidence_score, 0) / predictions.length
      : 0;

    return {
      total: predictions.length,
      urgent: urgent.length,
      converted: converted.length,
      average_confidence: avgConfidence,
    };
  }
}

export const predictionService = new PredictionService();