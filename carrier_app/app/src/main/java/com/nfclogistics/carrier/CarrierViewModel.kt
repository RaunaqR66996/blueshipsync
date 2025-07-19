package com.nfclogistics.carrier

import androidx.lifecycle.ViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import java.time.Instant
import java.time.ZoneOffset
import java.time.format.DateTimeFormatter

/**
 * ViewModel for the NFC Logistics Carrier App
 * Manages shipment state, NFC operations, and data persistence
 */
class CarrierViewModel : ViewModel() {
    
    // Active shipments that are in transit
    private val _activeShipments = MutableStateFlow<List<Map<String, Any>>>(emptyList())
    val activeShipments: StateFlow<List<Map<String, Any>>> = _activeShipments.asStateFlow()
    
    // Completed shipments history
    private val _completedShipments = MutableStateFlow<List<Map<String, Any>>>(emptyList())
    val completedShipments: StateFlow<List<Map<String, Any>>> = _completedShipments.asStateFlow()
    
    // Currently selected shipment for operations
    private val _selectedShipment = MutableStateFlow<Map<String, Any>?>(null)
    val selectedShipment: StateFlow<Map<String, Any>?> = _selectedShipment.asStateFlow()
    
    // NFC status
    private val _nfcStatus = MutableStateFlow("Ready")
    val nfcStatus: StateFlow<String> = _nfcStatus.asStateFlow()
    
    // Bridge connection status
    private val _bridgeStatus = MutableStateFlow("Disconnected")
    val bridgeStatus: StateFlow<String> = _bridgeStatus.asStateFlow()
    
    init {
        // Initialize with some sample data for testing
        loadSampleData()
    }
    
    private fun loadSampleData() {
        // Sample completed shipments for demonstration
        val sampleCompleted = listOf(
            mapOf(
                "transaction_id" to "TXN-ABC123DEF0",
                "status" to "confirmed",
                "completion_date" to "2024-01-15T10:30:00Z",
                "bol" to mapOf(
                    "number" to "BOL-SO-2024-001-20240115",
                    "origin" to "Westerville, OH",
                    "destination" to "Columbus, OH"
                )
            ),
            mapOf(
                "transaction_id" to "TXN-XYZ789GHI2",
                "status" to "confirmed", 
                "completion_date" to "2024-01-14T15:45:00Z",
                "bol" to mapOf(
                    "number" to "BOL-SO-2024-002-20240114",
                    "origin" to "Westerville, OH", 
                    "destination" to "Cincinnati, OH"
                )
            )
        )
        _completedShipments.value = sampleCompleted
    }
    
    /**
     * Add a new shipment received from NFC
     */
    fun addShipment(payload: Map<String, Any>) {
        val currentActive = _activeShipments.value.toMutableList()
        currentActive.add(payload)
        _activeShipments.value = currentActive
        
        // Auto-select the newly added shipment
        _selectedShipment.value = payload
    }
    
    /**
     * Select a shipment for operations
     */
    fun selectShipment(shipment: Map<String, Any>) {
        _selectedShipment.value = shipment
    }
    
    /**
     * Clear the selected shipment
     */
    fun clearSelection() {
        _selectedShipment.value = null
    }
    
    /**
     * Check if there's an active shipment selected
     */
    fun hasActiveShipment(): Boolean {
        return _selectedShipment.value != null
    }
    
    /**
     * Get the currently active payload for NFC operations
     */
    fun getActivePayload(): Map<String, Any> {
        return _selectedShipment.value ?: emptyMap()
    }
    
    /**
     * Complete a shipment (move from active to completed)
     */
    fun completeShipment(transactionId: String) {
        val currentActive = _activeShipments.value.toMutableList()
        val shipmentToComplete = currentActive.find { 
            it["transaction_id"] == transactionId 
        }
        
        shipmentToComplete?.let { shipment ->
            // Remove from active
            currentActive.removeIf { it["transaction_id"] == transactionId }
            _activeShipments.value = currentActive
            
            // Add to completed with completion timestamp
            val completedShipment = shipment.toMutableMap()
            completedShipment["status"] = "confirmed"
            completedShipment["completion_date"] = getCurrentTimestamp()
            
            val currentCompleted = _completedShipments.value.toMutableList()
            currentCompleted.add(0, completedShipment) // Add at beginning
            _completedShipments.value = currentCompleted
            
            // Clear selection if this was the selected shipment
            if (_selectedShipment.value?.get("transaction_id") == transactionId) {
                _selectedShipment.value = null
            }
        }
    }
    
    /**
     * Update shipment status
     */
    fun updateShipmentStatus(transactionId: String, newStatus: String) {
        // Update in active shipments
        val currentActive = _activeShipments.value.toMutableList()
        val activeIndex = currentActive.indexOfFirst { 
            it["transaction_id"] == transactionId 
        }
        
        if (activeIndex != -1) {
            val updatedShipment = currentActive[activeIndex].toMutableMap()
            updatedShipment["status"] = newStatus
            updatedShipment["timestamp"] = getCurrentTimestamp()
            
            // Add audit trail entry
            val auditTrail = (updatedShipment["audit_trail"] as? MutableList<Map<String, Any>>) 
                ?: mutableListOf()
            auditTrail.add(mapOf(
                "action" to "status_updated",
                "timestamp" to getCurrentTimestamp(),
                "actor" to "carrier_app",
                "location" to "Mobile Device",
                "notes" to "Status updated to $newStatus"
            ))
            updatedShipment["audit_trail"] = auditTrail
            
            currentActive[activeIndex] = updatedShipment
            _activeShipments.value = currentActive
            
            // Update selected shipment if it's the same one
            if (_selectedShipment.value?.get("transaction_id") == transactionId) {
                _selectedShipment.value = updatedShipment
            }
        }
    }
    
    /**
     * Set NFC status
     */
    fun setNfcStatus(status: String) {
        _nfcStatus.value = status
    }
    
    /**
     * Set bridge connection status  
     */
    fun setBridgeStatus(status: String) {
        _bridgeStatus.value = status
    }
    
    /**
     * Remove a shipment by transaction ID
     */
    fun removeShipment(transactionId: String) {
        val currentActive = _activeShipments.value.toMutableList()
        currentActive.removeIf { it["transaction_id"] == transactionId }
        _activeShipments.value = currentActive
        
        // Clear selection if this was the selected shipment
        if (_selectedShipment.value?.get("transaction_id") == transactionId) {
            _selectedShipment.value = null
        }
    }
    
    /**
     * Get shipment by transaction ID
     */
    fun getShipment(transactionId: String): Map<String, Any>? {
        return _activeShipments.value.find { it["transaction_id"] == transactionId }
    }
    
    /**
     * Get all shipments (active + completed)
     */
    fun getAllShipments(): List<Map<String, Any>> {
        return _activeShipments.value + _completedShipments.value
    }
    
    /**
     * Search shipments by BOL number, transaction ID, or other criteria
     */
    fun searchShipments(query: String): List<Map<String, Any>> {
        val allShipments = getAllShipments()
        return allShipments.filter { shipment ->
            val transactionId = shipment["transaction_id"] as? String ?: ""
            val bolNumber = (shipment["bol"] as? Map<String, Any>)?.get("number") as? String ?: ""
            val origin = (shipment["bol"] as? Map<String, Any>)?.get("origin") as? String ?: ""
            val destination = (shipment["bol"] as? Map<String, Any>)?.get("destination") as? String ?: ""
            
            transactionId.contains(query, ignoreCase = true) ||
            bolNumber.contains(query, ignoreCase = true) ||
            origin.contains(query, ignoreCase = true) ||
            destination.contains(query, ignoreCase = true)
        }
    }
    
    /**
     * Get shipment statistics
     */
    fun getShipmentStats(): Map<String, Int> {
        return mapOf(
            "active" to _activeShipments.value.size,
            "completed" to _completedShipments.value.size,
            "total" to (_activeShipments.value.size + _completedShipments.value.size)
        )
    }
    
    /**
     * Export shipment data for reporting
     */
    fun exportShipmentData(): String {
        val allShipments = getAllShipments()
        val gson = com.google.gson.Gson()
        return gson.toJson(mapOf(
            "export_timestamp" to getCurrentTimestamp(),
            "total_shipments" to allShipments.size,
            "active_shipments" to _activeShipments.value.size,
            "completed_shipments" to _completedShipments.value.size,
            "shipments" to allShipments
        ))
    }
    
    /**
     * Validate payload structure
     */
    fun validatePayload(payload: Map<String, Any>): Boolean {
        val requiredFields = listOf(
            "transaction_id", "status", "timestamp", "location",
            "packing_slip", "bol", "batch_details", "commercial_invoice",
            "pallet_count", "transit_type", "shipper_erp", "receiver_erp"
        )
        
        return requiredFields.all { field ->
            payload.containsKey(field) && payload[field] != null
        }
    }
    
    private fun getCurrentTimestamp(): String {
        return Instant.now()
            .atOffset(ZoneOffset.UTC)
            .format(DateTimeFormatter.ISO_INSTANT)
    }
}