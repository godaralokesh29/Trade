// frontend/src/api/tradeSageApi.js
const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

class TradeSageAPI {
  /**
   * Process a new trading hypothesis
   * @param {string} hypothesis - The trading hypothesis to process
   * @returns {Promise<Object>} The processed hypothesis data
   */
  async processHypothesis(hypothesis) {
    try {
      console.log('Sending request to:', `${API_BASE_URL}/process`);
      const requestBody = typeof hypothesis === 'string' 
        ? { hypothesis } 
        : hypothesis;
      
      console.log('Request body:', requestBody);
      
      const response = await fetch(`${API_BASE_URL}/process`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(requestBody),
      });
      
      if (!response.ok) {
        const errorText = await response.text();
        console.error('Error response:', errorText);
        let errorMessage = `HTTP error! status: ${response.status}`;
        
        try {
          const errorData = JSON.parse(errorText);
          if (errorData.detail) {
            errorMessage = Array.isArray(errorData.detail) 
              ? errorData.detail.map(d => d.msg).join(', ')
              : errorData.detail;
          }
        } catch (e) {
          console.error('Error parsing error response:', e);
        }
        
        throw new Error(errorMessage);
      }
      
      return await response.json();
    } catch (error) {
      console.error('Error in processHypothesis:', error);
      throw error;
    }
  }
  
  /**
   * Get all hypotheses summary for the dashboard
   * @returns {Promise<Array>} List of hypothesis summaries
   */
  async getAllHypotheses() {
    try {
      console.log('Fetching dashboard data from:', `${API_BASE_URL}/dashboard`);
      const response = await fetch(`${API_BASE_URL}/dashboard`);
      
      if (!response.ok) {
        const errorText = await response.text();
        console.error('Error response from /dashboard:', errorText);
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      // The backend returns the array directly
      const data = await response.json();
      console.log('Dashboard data received:', data);
      return { status: 'success', data };
    } catch (error) {
      console.error('Error fetching hypotheses:', error);
      throw error;
    }
  }
  
  /**
   * Get full details of a specific hypothesis
   * @param {string} hypothesisId - The ID of the hypothesis to fetch
   * @returns {Promise<Object>} The full hypothesis details
   */
  async getHypothesisById(hypothesisId) {
    try {
      console.log('Fetching hypothesis:', `${API_BASE_URL}/hypothesis/${hypothesisId}`);
      const response = await fetch(`${API_BASE_URL}/hypothesis/${hypothesisId}`);
      
      if (!response.ok) {
        const errorText = await response.text();
        console.error(`Error response for hypothesis ${hypothesisId}:`, errorText);
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      const data = await response.json();
      console.log('Hypothesis data received:', data);
      return data;
    } catch (error) {
      console.error(`Error fetching hypothesis ${hypothesisId}:`, error);
      throw error;
    }
  }

  /**
   * Get all alerts
   * @returns {Promise<Array>} List of alerts
   */
  async getAlerts() {
    try {
      const response = await fetch(`${API_BASE_URL}/alerts`);
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      return await response.json();
    } catch (error) {
      console.error('Error fetching alerts:', error);
      throw error;
    }
  }
  
  /**
   * Mark an alert as read
   * @param {string} alertId - The ID of the alert to mark as read
   * @returns {Promise<Object>} The updated alert
   */
  async markAlertAsRead(alertId) {
    try {
      const response = await fetch(`${API_BASE_URL}/alerts/${alertId}/read`, {
        method: 'PATCH',
      });
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      return await response.json();
    } catch (error) {
      console.error('Error marking alert as read:', error);
      throw error;
    }
  }
  
  /**
   * Check if the API is healthy
   * @returns {Promise<Object>} Health check status
   */
  async healthCheck() {
    try {
      const response = await fetch(`${API_BASE_URL}/health`);
      return await response.json();
    } catch (error) {
      console.error('Health check failed:', error);
      throw error;
    }
  }
  
  // Alias for backward compatibility
  async getDashboardData() {
    return this.getAllHypotheses();
  }
  
  // Alias for getHypothesisById for backward compatibility
  async getHypothesisDetail(hypothesisId) {
    return this.getHypothesisById(hypothesisId);
  }
}

// Create and export a singleton instance
const tradeSageAPI = new TradeSageAPI();

// Export as default to avoid constructor issues
export default {
  processHypothesis: (hypothesis) => tradeSageAPI.processHypothesis(hypothesis),
  getAllHypotheses: () => tradeSageAPI.getAllHypotheses(),
  getHypothesisById: (id) => tradeSageAPI.getHypothesisById(id),
  getHypothesisDetail: (id) => tradeSageAPI.getHypothesisDetail(id),
  getAlerts: () => tradeSageAPI.getAlerts(),
  markAlertAsRead: (id) => tradeSageAPI.markAlertAsRead(id),
  healthCheck: () => tradeSageAPI.healthCheck(),
  getDashboardData: () => tradeSageAPI.getDashboardData(),
};
