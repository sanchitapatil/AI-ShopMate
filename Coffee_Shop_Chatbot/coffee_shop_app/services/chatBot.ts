import axios, { AxiosError } from 'axios';
import { MessageInterface } from '@/types/types';
import { API_KEY, API_URL } from '@/config/runpodConfigs';

// Create axios instance with default config
const api = axios.create({
    baseURL: API_URL,
    timeout: 120000, // 2 minute timeout
    headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${API_KEY}`
    }
});

// Maximum number of retries
const MAX_RETRIES = 4;
// Base delay between retries (will be multiplied by attempt number)
const BASE_DELAY = 5000;

async function delay(ms: number) {
    return new Promise(resolve => setTimeout(resolve, ms));
}

async function callChatBotAPI(messages: MessageInterface[]): Promise<MessageInterface> {
    let attempt = 0;
    
    while (attempt < MAX_RETRIES) {
        try {
            const response = await api.post('', {
                input: { messages }
            });
            
            let output = response.data;
            let outputMessage: MessageInterface = output['output'];

            return outputMessage;
        } catch (error) {
            attempt++;
            
            if (error instanceof AxiosError) {
                // Log detailed error information
                console.error('API Error:', {
                    status: error.response?.status,
                    statusText: error.response?.statusText,
                    data: error.response?.data,
                    attempt
                });

                // If it's the last attempt, throw the error
                if (attempt === MAX_RETRIES) {
                    if (error.code === 'ECONNABORTED') {
                        throw new Error('Request timed out. Please try again.');
                    }
                    throw new Error('Failed to get response from chatbot. Please try again.');
                }

                // Wait before retrying, with exponential backoff
                await delay(BASE_DELAY * attempt);
                continue;
            }

            // For non-axios errors, throw immediately
            throw error;
        }
    }

    // This should never be reached due to the throw in the last attempt
    throw new Error('Failed to get response from chatbot after multiple attempts.');
}

export { callChatBotAPI };
