// src/utils/pushNotifications.ts
import axios from 'axios';
import { NotifToken, INotifToken } from '../models/NotifToken';

// TypeScript interfaces for Expo push notifications
export interface ExpoPushMessage {
  to: string | string[];
  sound?: 'default' | null;
  title?: string;
  body?: string;
  data?: Record<string, any>;
  ttl?: number;
  expiration?: number;
  priority?: 'default' | 'normal' | 'high';
  subtitle?: string;
  badge?: number;
  channelId?: string;
}

export interface ExpoPushTicket {
  id?: string;
  status: 'ok' | 'error';
  message?: string;
  details?: {
    error?: 'InvalidCredentials' | 'MessageTooBig' | 'MessageRateExceeded' | 'MismatchSenderId' | 'InvalidProviderToken' | 'DeviceNotRegistered' | 'ExpoError';
  };
}

export interface ExpoPushReceiptResponse {
  [ticketId: string]: {
    status: 'ok' | 'error';
    message?: string;
    details?: {
      error?: string;
    };
  };
}

export interface PushNotificationResult {
  success: boolean;
  tickets?: ExpoPushTicket[];
  error?: string;
  userId?: string;
}

export interface BulkNotificationResult {
  totalSent: number;
  successful: number;
  failed: number;
  results: PushNotificationResult[];
}

// Expo push notification endpoint
const EXPO_PUSH_ENDPOINT = 'https://exp.host/--/api/v2/push/send';
const EXPO_RECEIPT_ENDPOINT = 'https://exp.host/--/api/v2/push/getReceipts';

// Maximum batch size for Expo push notifications
const EXPO_BATCH_SIZE = 100;

/**
 * Sends a push notification to a single user
 * @param userId - The user ID to send the notification to
 * @param title - The notification title
 * @param body - The notification body text
 * @param data - Optional additional data to include
 * @returns Promise with the result of the notification send
 */
export async function sendPushNotification(
  userId: string,
  title: string,
  body: string,
  data?: Record<string, any>
): Promise<PushNotificationResult> {
  try {
    // Look up the user's Expo push token from the database
    const notifToken = await NotifToken.findOne({ cust_id: userId }).lean();
    
    if (!notifToken || !notifToken.token) {
      console.warn(`No push token found for user: ${userId}`);
      return {
        success: false,
        error: 'No push token found for user',
        userId
      };
    }

    // Validate that the token looks like an Expo push token
    if (!isValidExpoToken(notifToken.token)) {
      console.error(`Invalid Expo push token for user ${userId}: ${notifToken.token}`);
      return {
        success: false,
        error: 'Invalid Expo push token format',
        userId
      };
    }

    // Prepare the notification message
    const message: ExpoPushMessage = {
      to: notifToken.token,
      sound: 'default',
      title,
      body,
      ...(data && { data })
    };

    // Send the notification to Expo's push service
    const response = await axios.post<ExpoPushTicket[]>(
      EXPO_PUSH_ENDPOINT,
      message,
      {
        headers: {
          'Accept': 'application/json',
          'Accept-encoding': 'gzip, deflate',
          'Content-Type': 'application/json',
        },
        timeout: 10000 // 10 second timeout
      }
    );

    if (response.data && response.data.length > 0) {
      const ticket = response.data[0];
      
      if (ticket.status === 'error') {
        console.error(`Failed to send push notification to user ${userId}:`, ticket.message);
        
        // Handle specific error cases
        if (ticket.details?.error === 'DeviceNotRegistered') {
          // Token is invalid, consider removing it from the database
          console.warn(`Device not registered for user ${userId}, token may be expired`);
        }
        
        return {
          success: false,
          error: ticket.message || 'Unknown error from Expo',
          tickets: response.data,
          userId
        };
      }

      console.log(`Successfully sent push notification to user ${userId}`);
      return {
        success: true,
        tickets: response.data,
        userId
      };
    } else {
      return {
        success: false,
        error: 'No response data from Expo',
        userId
      };
    }

  } catch (error) {
    console.error(`Error sending push notification to user ${userId}:`, error);
    
    let errorMessage = 'Unknown error occurred';
    if (error && typeof error === 'object' && 'response' in error) {
      // This is likely an axios error
      const axiosError = error as any;
      errorMessage = axiosError.response?.data?.message || axiosError.message || 'HTTP request failed';
    } else if (error instanceof Error) {
      errorMessage = error.message;
    }

    return {
      success: false,
      error: errorMessage,
      userId
    };
  }
}

/**
 * Sends push notifications to multiple users in batches
 * @param userIds - Array of user IDs to send notifications to
 * @param title - The notification title
 * @param body - The notification body text
 * @param data - Optional additional data to include
 * @returns Promise with bulk notification results
 */
export async function sendBulkNotifications(
  userIds: string[],
  title: string,
  body: string,
  data?: Record<string, any>
): Promise<BulkNotificationResult> {
  try {
    // Query all notification tokens for the provided user IDs
    const notifTokens = await NotifToken.find({ 
      cust_id: { $in: userIds } 
    }).lean();

    if (notifTokens.length === 0) {
      console.warn('No push tokens found for any of the provided user IDs');
      return {
        totalSent: 0,
        successful: 0,
        failed: userIds.length,
        results: userIds.map(userId => ({
          success: false,
          error: 'No push token found for user',
          userId
        }))
      };
    }

    // Create a map of user IDs to tokens for easier lookup
    const tokenMap = new Map<string, string>();
    notifTokens.forEach(token => {
      if (isValidExpoToken(token.token)) {
        tokenMap.set(token.cust_id, token.token);
      }
    });

    // Prepare messages for users with valid tokens
    const messages: ExpoPushMessage[] = [];
    const userIdToMessageIndex: Map<string, number> = new Map();

    userIds.forEach(userId => {
      const token = tokenMap.get(userId);
      if (token) {
        const messageIndex = messages.length;
        userIdToMessageIndex.set(userId, messageIndex);
        
        messages.push({
          to: token,
          sound: 'default',
          title,
          body,
          ...(data && { data })
        });
      }
    });

    if (messages.length === 0) {
      console.warn('No valid push tokens found for bulk notification');
      return {
        totalSent: 0,
        successful: 0,
        failed: userIds.length,
        results: userIds.map(userId => ({
          success: false,
          error: 'No valid push token found for user',
          userId
        }))
      };
    }

    // Split messages into batches of 100 (Expo's limit)
    const batches: ExpoPushMessage[][] = [];
    for (let i = 0; i < messages.length; i += EXPO_BATCH_SIZE) {
      batches.push(messages.slice(i, i + EXPO_BATCH_SIZE));
    }

    console.log(`Sending ${messages.length} notifications in ${batches.length} batch(es)`);

    // Send each batch
    const allResults: PushNotificationResult[] = [];
    let successful = 0;
    let failed = 0;

    for (let batchIndex = 0; batchIndex < batches.length; batchIndex++) {
      const batch = batches[batchIndex];
      
      try {
        const response = await axios.post<ExpoPushTicket[]>(
          EXPO_PUSH_ENDPOINT,
          batch,
          {
            headers: {
              'Accept': 'application/json',
              'Accept-encoding': 'gzip, deflate',
              'Content-Type': 'application/json',
            },
            timeout: 15000 // 15 second timeout for batch requests
          }
        );

        if (response.data && Array.isArray(response.data)) {
          // Process each ticket in the response
          response.data.forEach((ticket, ticketIndex) => {
            const globalMessageIndex = (batchIndex * EXPO_BATCH_SIZE) + ticketIndex;
            const userId = findUserIdByMessageIndex(userIdToMessageIndex, globalMessageIndex);
            
            const result: PushNotificationResult = {
              success: ticket.status === 'ok',
              tickets: [ticket],
              userId,
              ...(ticket.status === 'error' && { error: ticket.message || 'Unknown error from Expo' })
            };

            allResults.push(result);
            
            if (ticket.status === 'ok') {
              successful++;
            } else {
              failed++;
              console.error(`Failed to send notification in batch ${batchIndex + 1}:`, ticket.message);
            }
          });
        } else {
          // Handle case where batch failed entirely
          batch.forEach((_, messageIndex) => {
            const globalMessageIndex = (batchIndex * EXPO_BATCH_SIZE) + messageIndex;
            const userId = findUserIdByMessageIndex(userIdToMessageIndex, globalMessageIndex);
            
            allResults.push({
              success: false,
              error: 'No response data from Expo for batch',
              userId
            });
            failed++;
          });
        }

      } catch (batchError) {
        console.error(`Error sending batch ${batchIndex + 1}:`, batchError);
        
        // Mark all messages in this batch as failed
        batch.forEach((_, messageIndex) => {
          const globalMessageIndex = (batchIndex * EXPO_BATCH_SIZE) + messageIndex;
          const userId = findUserIdByMessageIndex(userIdToMessageIndex, globalMessageIndex);
          
          let errorMessage = 'Batch request failed';
          if (batchError && typeof batchError === 'object' && 'response' in batchError) {
            // This is likely an axios error
            const axiosError = batchError as any;
            errorMessage = axiosError.response?.data?.message || axiosError.message || 'HTTP request failed';
          } else if (batchError instanceof Error) {
            errorMessage = batchError.message;
          }

          allResults.push({
            success: false,
            error: errorMessage,
            userId
          });
          failed++;
        });
      }

      // Add a small delay between batches to avoid rate limiting
      if (batchIndex < batches.length - 1) {
        await new Promise(resolve => setTimeout(resolve, 100));
      }
    }

    // Add results for users who didn't have valid tokens
    userIds.forEach(userId => {
      if (!tokenMap.has(userId)) {
        allResults.push({
          success: false,
          error: 'No valid push token found for user',
          userId
        });
        failed++;
      }
    });

    console.log(`Bulk notification complete: ${successful} successful, ${failed} failed`);

    return {
      totalSent: messages.length,
      successful,
      failed,
      results: allResults
    };

  } catch (error) {
    console.error('Error in bulk notification send:', error);
    
    let errorMessage = 'Unknown error occurred during bulk send';
    if (error instanceof Error) {
      errorMessage = error.message;
    }

    return {
      totalSent: 0,
      successful: 0,
      failed: userIds.length,
      results: userIds.map(userId => ({
        success: false,
        error: errorMessage,
        userId
      }))
    };
  }
}

/**
 * Checks if a token is a valid Expo push token format
 * @param token - The token to validate
 * @returns boolean indicating if the token is valid
 */
function isValidExpoToken(token: string): boolean {
  // Expo push tokens start with ExponentPushToken[ or ExpoPushToken[
  return /^(ExponentPushToken|ExpoPushToken)\[.+\]$/.test(token);
}

/**
 * Helper function to find user ID by message index in the batch
 * @param userIdToMessageIndex - Map of user IDs to message indices
 * @param messageIndex - The global message index
 * @returns The user ID or undefined
 */
function findUserIdByMessageIndex(
  userIdToMessageIndex: Map<string, number>,
  messageIndex: number
): string | undefined {
  for (const [userId, index] of userIdToMessageIndex.entries()) {
    if (index === messageIndex) {
      return userId;
    }
  }
  return undefined;
}

/**
 * Retrieves push notification receipts from Expo
 * This can be used to check the final delivery status of notifications
 * @param ticketIds - Array of ticket IDs from previous push operations
 * @returns Promise with receipt information
 */
export async function getPushNotificationReceipts(
  ticketIds: string[]
): Promise<{ success: boolean; receipts?: ExpoPushReceiptResponse; error?: string }> {
  try {
    if (ticketIds.length === 0) {
      return {
        success: false,
        error: 'No ticket IDs provided'
      };
    }

    const response = await axios.post<ExpoPushReceiptResponse>(
      EXPO_RECEIPT_ENDPOINT,
      { ids: ticketIds },
      {
        headers: {
          'Accept': 'application/json',
          'Accept-encoding': 'gzip, deflate',
          'Content-Type': 'application/json',
        },
        timeout: 10000
      }
    );

    return {
      success: true,
      receipts: response.data
    };

  } catch (error) {
    console.error('Error fetching push notification receipts:', error);
    
    let errorMessage = 'Unknown error occurred';
    if (error && typeof error === 'object' && 'response' in error) {
      // This is likely an axios error
      const axiosError = error as any;
      errorMessage = axiosError.response?.data?.message || axiosError.message || 'HTTP request failed';
    } else if (error instanceof Error) {
      errorMessage = error.message;
    }

    return {
      success: false,
      error: errorMessage
    };
  }
}