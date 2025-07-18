package com.logistics.nfc.model

import com.google.gson.Gson
import com.google.gson.annotations.SerializedName
import java.util.*

data class ShipmentPayload(
    @SerializedName("transaction")
    val transaction: Transaction,
    
    @SerializedName("packing_slip")
    val packingSlip: PackingSlip,
    
    @SerializedName("bill_of_lading")
    val billOfLading: BillOfLading,
    
    @SerializedName("batch_details")
    val batchDetails: BatchDetails,
    
    @SerializedName("commercial_invoice")
    val commercialInvoice: CommercialInvoice,
    
    @SerializedName("erp_identifiers")
    val erpIdentifiers: ERPIdentifiers,
    
    @SerializedName("security")
    val security: Security,
    
    @SerializedName("metadata")
    val metadata: Metadata
) {
    fun toJson(): String {
        return Gson().toJson(this)
    }
    
    companion object {
        fun fromJson(json: String): ShipmentPayload {
            return Gson().fromJson(json, ShipmentPayload::class.java)
        }
    }
}

data class Transaction(
    @SerializedName("transaction_id")
    val transactionId: String,
    
    @SerializedName("status")
    val status: String,
    
    @SerializedName("timestamp")
    val timestamp: String,
    
    @SerializedName("location")
    val location: Location
)

data class Location(
    @SerializedName("latitude")
    val latitude: Double,
    
    @SerializedName("longitude")
    val longitude: Double,
    
    @SerializedName("address")
    val address: String,
    
    @SerializedName("city")
    val city: String,
    
    @SerializedName("state")
    val state: String,
    
    @SerializedName("zip_code")
    val zipCode: String
)

data class PackingSlip(
    @SerializedName("items")
    val items: List<Item>,
    
    @SerializedName("total_weight")
    val totalWeight: Double,
    
    @SerializedName("total_items")
    val totalItems: Int,
    
    @SerializedName("pallet_count")
    val palletCount: Int
)

data class Item(
    @SerializedName("item_id")
    val itemId: String,
    
    @SerializedName("description")
    val description: String,
    
    @SerializedName("quantity")
    val quantity: Int,
    
    @SerializedName("unit_weight")
    val unitWeight: Double,
    
    @SerializedName("total_weight")
    val totalWeight: Double,
    
    @SerializedName("sku")
    val sku: String,
    
    @SerializedName("lot_number")
    val lotNumber: String
)

data class BillOfLading(
    @SerializedName("bol_number")
    val bolNumber: String,
    
    @SerializedName("carrier_name")
    val carrierName: String,
    
    @SerializedName("carrier_id")
    val carrierId: String,
    
    @SerializedName("transit_type")
    val transitType: String,
    
    @SerializedName("origin")
    val origin: String,
    
    @SerializedName("destination")
    val destination: String,
    
    @SerializedName("pickup_date")
    val pickupDate: String,
    
    @SerializedName("delivery_date")
    val deliveryDate: String
)

data class BatchDetails(
    @SerializedName("batch_id")
    val batchId: String,
    
    @SerializedName("manufacture_date")
    val manufactureDate: String,
    
    @SerializedName("expiry_date")
    val expiryDate: String,
    
    @SerializedName("batch_size")
    val batchSize: Int,
    
    @SerializedName("quality_grade")
    val qualityGrade: String
)

data class CommercialInvoice(
    @SerializedName("invoice_number")
    val invoiceNumber: String,
    
    @SerializedName("total_value")
    val totalValue: Double,
    
    @SerializedName("currency")
    val currency: String,
    
    @SerializedName("payment_terms")
    val paymentTerms: String,
    
    @SerializedName("incoterms")
    val incoterms: String,
    
    @SerializedName("tax_amount")
    val taxAmount: Double
)

data class ERPIdentifiers(
    @SerializedName("shipper_erp_id")
    val shipperErpId: String,
    
    @SerializedName("shipper_erp_type")
    val shipperErpType: String,
    
    @SerializedName("receiver_erp_id")
    val receiverErpId: String,
    
    @SerializedName("receiver_erp_type")
    val receiverErpType: String,
    
    @SerializedName("carrier_erp_id")
    val carrierErpId: String
)

data class Security(
    @SerializedName("digital_signature")
    val digitalSignature: String,
    
    @SerializedName("signature_algorithm")
    val signatureAlgorithm: String,
    
    @SerializedName("signature_timestamp")
    val signatureTimestamp: String,
    
    @SerializedName("encryption_key_id")
    val encryptionKeyId: String,
    
    @SerializedName("checksum")
    val checksum: String
)

data class Metadata(
    @SerializedName("version")
    val version: String,
    
    @SerializedName("created_by")
    val createdBy: String,
    
    @SerializedName("last_modified")
    val lastModified: String,
    
    @SerializedName("priority")
    val priority: String,
    
    @SerializedName("special_instructions")
    val specialInstructions: String
)