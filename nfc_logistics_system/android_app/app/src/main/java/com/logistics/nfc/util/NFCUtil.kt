package com.logistics.nfc.util

import android.nfc.NdefMessage
import android.nfc.NdefRecord
import android.nfc.Tag
import android.nfc.tech.Ndef
import android.util.Log
import com.logistics.nfc.model.ShipmentPayload
import java.io.IOException
import java.nio.charset.StandardCharsets

class NFCUtil {
    
    companion object {
        private const val TAG = "NFCUtil"
        private const val MIME_TYPE = "application/vnd.logistics.shipment"
    }
    
    /**
     * Read shipment payload from NFC tag
     */
    fun readShipmentPayload(tag: Tag): ShipmentPayload? {
        val ndef = Ndef.get(tag) ?: return null
        
        return try {
            ndef.connect()
            val ndefMessage = ndef.cachedNdefMessage ?: ndef.readNdefMessage()
            val records = ndefMessage.records
            
            for (record in records) {
                if (record.toMimeType() == MIME_TYPE) {
                    val payloadString = String(record.payload, StandardCharsets.UTF_8)
                    return ShipmentPayload.fromJson(payloadString)
                }
            }
            null
        } catch (e: IOException) {
            Log.e(TAG, "Error reading NFC payload", e)
            null
        } finally {
            try {
                ndef.close()
            } catch (e: IOException) {
                Log.e(TAG, "Error closing NFC connection", e)
            }
        }
    }
    
    /**
     * Write shipment payload to NFC tag
     */
    fun writeShipmentPayload(tag: Tag, payload: ShipmentPayload): Boolean {
        val ndef = Ndef.get(tag) ?: return false
        
        return try {
            ndef.connect()
            
            val payloadJson = payload.toJson()
            val payloadBytes = payloadJson.toByteArray(StandardCharsets.UTF_8)
            
            val record = NdefRecord.createMime(MIME_TYPE, payloadBytes)
            val ndefMessage = NdefMessage(arrayOf(record))
            
            ndef.writeNdefMessage(ndefMessage)
            true
        } catch (e: IOException) {
            Log.e(TAG, "Error writing NFC payload", e)
            false
        } finally {
            try {
                ndef.close()
            } catch (e: IOException) {
                Log.e(TAG, "Error closing NFC connection", e)
            }
        }
    }
    
    /**
     * Check if tag supports NDEF
     */
    fun isNdefSupported(tag: Tag): Boolean {
        return Ndef.get(tag) != null
    }
    
    /**
     * Get tag information
     */
    fun getTagInfo(tag: Tag): TagInfo {
        val ndef = Ndef.get(tag)
        return TagInfo(
            id = bytesToHexString(tag.id),
            technologies = tag.techList.toList(),
            isNdefSupported = ndef != null,
            ndefSize = ndef?.maxSize ?: 0,
            ndefType = ndef?.type?.name ?: "Unknown"
        )
    }
    
    /**
     * Convert byte array to hex string
     */
    private fun bytesToHexString(bytes: ByteArray): String {
        val hexChars = CharArray(bytes.size * 2)
        for (i in bytes.indices) {
            val v = bytes[i].toInt() and 0xFF
            hexChars[i * 2] = "0123456789ABCDEF"[v ushr 4]
            hexChars[i * 2 + 1] = "0123456789ABCDEF"[v and 0x0F]
        }
        return String(hexChars)
    }
    
    /**
     * Validate payload before writing
     */
    fun validatePayloadForWriting(payload: ShipmentPayload): ValidationResult {
        val errors = mutableListOf<String>()
        
        // Check required fields
        if (payload.transaction.transactionId.isBlank()) {
            errors.add("Transaction ID is required")
        }
        
        if (payload.billOfLading.bolNumber.isBlank()) {
            errors.add("BOL number is required")
        }
        
        if (payload.packingSlip.items.isEmpty()) {
            errors.add("At least one item is required")
        }
        
        if (payload.erpIdentifiers.receiverErpId.isBlank()) {
            errors.add("Receiver ERP ID is required")
        }
        
        // Check payload size (NFC tags have limited storage)
        val payloadSize = payload.toJson().toByteArray(StandardCharsets.UTF_8).size
        if (payloadSize > 4096) { // 4KB limit for most NFC tags
            errors.add("Payload size exceeds NFC tag capacity")
        }
        
        return ValidationResult(
            isValid = errors.isEmpty(),
            errors = errors
        )
    }
    
    data class TagInfo(
        val id: String,
        val technologies: List<String>,
        val isNdefSupported: Boolean,
        val ndefSize: Int,
        val ndefType: String
    )
    
    data class ValidationResult(
        val isValid: Boolean,
        val errors: List<String>
    )
}