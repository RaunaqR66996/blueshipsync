package com.logistics.nfc.network

import android.util.Log
import com.logistics.nfc.model.ShipmentPayload
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import okhttp3.*
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.RequestBody.Companion.toRequestBody
import org.json.JSONObject
import java.io.IOException
import java.net.Socket
import java.util.concurrent.TimeUnit

class NetworkManager {
    
    companion object {
        private const val TAG = "NetworkManager"
        private const val SHIPPER_HOST = "localhost"
        private const val SHIPPER_PORT = 65432
        private const val RECEIVER_HOST = "localhost"
        private const val RECEIVER_PORT = 65433
        private const val TIMEOUT_SECONDS = 30L
    }
    
    private val client = OkHttpClient.Builder()
        .connectTimeout(TIMEOUT_SECONDS, TimeUnit.SECONDS)
        .readTimeout(TIMEOUT_SECONDS, TimeUnit.SECONDS)
        .writeTimeout(TIMEOUT_SECONDS, TimeUnit.SECONDS)
        .build()
    
    private val jsonMediaType = "application/json; charset=utf-8".toMediaType()
    
    data class NetworkResponse(
        val isSuccessful: Boolean,
        val data: String? = null,
        val error: String? = null
    )
    
    suspend fun connectToShipper(): NetworkResponse = withContext(Dispatchers.IO) {
        try {
            val socket = Socket(SHIPPER_HOST, SHIPPER_PORT)
            socket.close()
            NetworkResponse(true, "Connected to shipper")
        } catch (e: Exception) {
            Log.e(TAG, "Error connecting to shipper", e)
            NetworkResponse(false, error = e.message)
        }
    }
    
    suspend fun connectToReceiver(): NetworkResponse = withContext(Dispatchers.IO) {
        try {
            val socket = Socket(RECEIVER_HOST, RECEIVER_PORT)
            socket.close()
            NetworkResponse(true, "Connected to receiver")
        } catch (e: Exception) {
            Log.e(TAG, "Error connecting to receiver", e)
            NetworkResponse(false, error = e.message)
        }
    }
    
    suspend fun syncPayloadWithBridge(payload: ShipmentPayload): NetworkResponse = withContext(Dispatchers.IO) {
        try {
            val payloadJson = payload.toJson()
            val requestBody = payloadJson.toRequestBody(jsonMediaType)
            
            val request = Request.Builder()
                .url("http://$SHIPPER_HOST:$SHIPPER_PORT/sync")
                .post(requestBody)
                .build()
            
            client.newCall(request).execute().use { response ->
                val responseBody = response.body?.string()
                return@withContext if (response.isSuccessful) {
                    NetworkResponse(true, responseBody)
                } else {
                    NetworkResponse(false, error = "HTTP ${response.code}: $responseBody")
                }
            }
        } catch (e: Exception) {
            Log.e(TAG, "Error syncing payload", e)
            NetworkResponse(false, error = e.message)
        }
    }
    
    suspend fun sendPayloadToShipper(payload: ShipmentPayload): NetworkResponse = withContext(Dispatchers.IO) {
        try {
            val requestData = JSONObject().apply {
                put("type", "create_shipment")
                put("shipment_data", JSONObject(payload.toJson()))
            }
            
            val requestBody = requestData.toString().toRequestBody(jsonMediaType)
            
            val request = Request.Builder()
                .url("http://$SHIPPER_HOST:$SHIPPER_PORT")
                .post(requestBody)
                .build()
            
            client.newCall(request).execute().use { response ->
                val responseBody = response.body?.string()
                return@withContext if (response.isSuccessful) {
                    NetworkResponse(true, responseBody)
                } else {
                    NetworkResponse(false, error = "HTTP ${response.code}: $responseBody")
                }
            }
        } catch (e: Exception) {
            Log.e(TAG, "Error sending payload to shipper", e)
            NetworkResponse(false, error = e.message)
        }
    }
    
    suspend fun deliverPayloadToReceiver(payload: ShipmentPayload): NetworkResponse = withContext(Dispatchers.IO) {
        try {
            val requestData = JSONObject().apply {
                put("type", "deliver_shipment")
                put("payload", JSONObject(payload.toJson()))
            }
            
            val requestBody = requestData.toString().toRequestBody(jsonMediaType)
            
            val request = Request.Builder()
                .url("http://$RECEIVER_HOST:$RECEIVER_PORT")
                .post(requestBody)
                .build()
            
            client.newCall(request).execute().use { response ->
                val responseBody = response.body?.string()
                return@withContext if (response.isSuccessful) {
                    NetworkResponse(true, responseBody)
                } else {
                    NetworkResponse(false, error = "HTTP ${response.code}: $responseBody")
                }
            }
        } catch (e: Exception) {
            Log.e(TAG, "Error delivering payload to receiver", e)
            NetworkResponse(false, error = e.message)
        }
    }
    
    suspend fun validatePayload(payload: ShipmentPayload): NetworkResponse = withContext(Dispatchers.IO) {
        try {
            val requestData = JSONObject().apply {
                put("type", "validate_payload")
                put("payload", JSONObject(payload.toJson()))
            }
            
            val requestBody = requestData.toString().toRequestBody(jsonMediaType)
            
            val request = Request.Builder()
                .url("http://$RECEIVER_HOST:$RECEIVER_PORT")
                .post(requestBody)
                .build()
            
            client.newCall(request).execute().use { response ->
                val responseBody = response.body?.string()
                return@withContext if (response.isSuccessful) {
                    NetworkResponse(true, responseBody)
                } else {
                    NetworkResponse(false, error = "HTTP ${response.code}: $responseBody")
                }
            }
        } catch (e: Exception) {
            Log.e(TAG, "Error validating payload", e)
            NetworkResponse(false, error = e.message)
        }
    }
    
    suspend fun getShipmentStatus(transactionId: String): NetworkResponse = withContext(Dispatchers.IO) {
        try {
            val requestData = JSONObject().apply {
                put("type", "get_shipment_status")
                put("transaction_id", transactionId)
            }
            
            val requestBody = requestData.toString().toRequestBody(jsonMediaType)
            
            val request = Request.Builder()
                .url("http://$SHIPPER_HOST:$SHIPPER_PORT")
                .post(requestBody)
                .build()
            
            client.newCall(request).execute().use { response ->
                val responseBody = response.body?.string()
                return@withContext if (response.isSuccessful) {
                    NetworkResponse(true, responseBody)
                } else {
                    NetworkResponse(false, error = "HTTP ${response.code}: $responseBody")
                }
            }
        } catch (e: Exception) {
            Log.e(TAG, "Error getting shipment status", e)
            NetworkResponse(false, error = e.message)
        }
    }
    
    suspend fun getCompletionStatus(transactionId: String): NetworkResponse = withContext(Dispatchers.IO) {
        try {
            val requestData = JSONObject().apply {
                put("type", "get_completion_status")
                put("transaction_id", transactionId)
            }
            
            val requestBody = requestData.toString().toRequestBody(jsonMediaType)
            
            val request = Request.Builder()
                .url("http://$RECEIVER_HOST:$RECEIVER_PORT")
                .post(requestBody)
                .build()
            
            client.newCall(request).execute().use { response ->
                val responseBody = response.body?.string()
                return@withContext if (response.isSuccessful) {
                    NetworkResponse(true, responseBody)
                } else {
                    NetworkResponse(false, error = "HTTP ${response.code}: $responseBody")
                }
            }
        } catch (e: Exception) {
            Log.e(TAG, "Error getting completion status", e)
            NetworkResponse(false, error = e.message)
        }
    }
    
    fun close() {
        client.dispatcher.executorService.shutdown()
        client.connectionPool.evictAll()
    }
}