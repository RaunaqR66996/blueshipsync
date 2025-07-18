package com.logistics.carrier

import android.app.PendingIntent
import android.content.Intent
import android.content.IntentFilter
import android.nfc.NdefMessage
import android.nfc.NdefRecord
import android.nfc.NfcAdapter
import android.nfc.Tag
import android.nfc.tech.Ndef
import android.os.Bundle
import android.util.Log
import android.widget.Toast
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.lifecycle.viewmodel.compose.viewModel
import com.google.android.gms.wallet.*
import com.google.gson.Gson
import kotlinx.coroutines.*
import okhttp3.*
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.RequestBody.Companion.toRequestBody
import org.json.JSONObject
import java.io.IOException
import java.text.SimpleDateFormat
import java.util.*

// Data classes for the logistics payload
data class Transaction(
    val id: String,
    val status: String,
    val timestamp: String,
    val location: Location
)

data class Location(
    val latitude: Double,
    val longitude: Double,
    val address: String
)

data class PackingSlipItem(
    val sku: String,
    val description: String,
    val quantity: Int,
    val weight: Double,
    val unit: String
)

data class PackingSlip(
    val items: List<PackingSlipItem>,
    val total_weight: Double,
    val weight_unit: String
)

data class BOL(
    val number: String,
    val date: String,
    val carrier_name: String,
    val carrier_id: String
)

data class BatchDetails(
    val batch_id: String,
    val manufacture_date: String,
    val expiry_date: String,
    val lot_numbers: List<String>
)

data class CommercialInvoice(
    val number: String,
    val date: String,
    val total_value: Double,
    val currency: String,
    val terms: String
)

data class Logistics(
    val pallet_count: Int,
    val transit_type: String,
    val vehicle_id: String,
    val driver_id: String
)

data class ERPIdentifier(
    val system: String,
    val company_id: String,
    val order_id: String? = null,
    val po_number: String? = null
)

data class ERPIdentifiers(
    val shipper: ERPIdentifier,
    val receiver: ERPIdentifier
)

data class Security(
    val digital_signature: String,
    val signature_algorithm: String,
    val signature_timestamp: String,
    val public_key_id: String,
    val public_key: String? = null
)

data class ShipmentPayload(
    val transaction: Transaction,
    val packing_slip: PackingSlip,
    val bol: BOL,
    val batch_details: BatchDetails,
    val commercial_invoice: CommercialInvoice,
    val logistics: Logistics,
    val erp_identifiers: ERPIdentifiers,
    val security: Security
)

// ViewModel for managing app state
class CarrierViewModel : androidx.lifecycle.ViewModel() {
    private val _shipments = mutableStateListOf<ShipmentPayload>()
    val shipments: List<ShipmentPayload> = _shipments
    
    private val _isConnected = mutableStateOf(false)
    val isConnected: State<Boolean> = _isConnected
    
    private val _selectedShipment = mutableStateOf<ShipmentPayload?>(null)
    val selectedShipment: State<ShipmentPayload?> = _selectedShipment
    
    private var webSocket: WebSocket? = null
    private val client = OkHttpClient()
    private val gson = Gson()
    
    fun connectToBridge(bridgeUrl: String, carrierId: String) {
        val request = Request.Builder()
            .url(bridgeUrl)
            .build()
        
        webSocket = client.newWebSocket(request, object : WebSocketListener() {
            override fun onOpen(webSocket: WebSocket, response: Response) {
                Log.d("CarrierApp", "WebSocket connected")
                _isConnected.value = true
                
                // Register carrier
                val registerMessage = JSONObject().apply {
                    put("type", "carrier_register")
                    put("carrier_id", carrierId)
                }
                webSocket.send(registerMessage.toString())
            }
            
            override fun onMessage(webSocket: WebSocket, text: String) {
                try {
                    val message = JSONObject(text)
                    when (message.getString("type")) {
                        "new_shipment" -> {
                            val payloadJson = message.getJSONObject("payload")
                            val shipment = gson.fromJson(payloadJson.toString(), ShipmentPayload::class.java)
                            _shipments.add(shipment)
                            
                            // Acknowledge receipt
                            val ackMessage = JSONObject().apply {
                                put("type", "payload_received")
                                put("transaction_id", shipment.transaction.id)
                            }
                            webSocket.send(ackMessage.toString())
                        }
                    }
                } catch (e: Exception) {
                    Log.e("CarrierApp", "Error processing message", e)
                }
            }
            
            override fun onFailure(webSocket: WebSocket, t: Throwable, response: Response?) {
                Log.e("CarrierApp", "WebSocket failure", t)
                _isConnected.value = false
            }
            
            override fun onClosed(webSocket: WebSocket, code: Int, reason: String) {
                Log.d("CarrierApp", "WebSocket closed: $reason")
                _isConnected.value = false
            }
        })
    }
    
    fun selectShipment(shipment: ShipmentPayload) {
        _selectedShipment.value = shipment
    }
    
    fun addToGoogleWallet(activity: ComponentActivity, shipment: ShipmentPayload) {
        // Create Google Wallet pass for the shipment
        val walletClient = Wallet.getWalletClient(activity)
        
        // In production, this would create an actual Google Wallet pass
        // For now, we'll simulate storing in Google Wallet
        Log.d("CarrierApp", "Adding shipment ${shipment.transaction.id} to Google Wallet")
        
        // Update shipment status
        shipment.transaction.copy(status = "in_transit")
    }
    
    fun reportDelivery(transactionId: String) {
        webSocket?.let { ws ->
            val deliveryMessage = JSONObject().apply {
                put("type", "delivery_completed")
                put("transaction_id", transactionId)
                put("timestamp", SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ss'Z'", Locale.UTC).format(Date()))
            }
            ws.send(deliveryMessage.toString())
        }
    }
    
    override fun onCleared() {
        super.onCleared()
        webSocket?.close(1000, "ViewModel cleared")
    }
}

class MainActivity : ComponentActivity() {
    private var nfcAdapter: NfcAdapter? = null
    private lateinit var viewModel: CarrierViewModel
    private val carrierId = "CARR-OH-${UUID.randomUUID().toString().substring(0, 6).uppercase()}"
    
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        
        // Initialize NFC
        nfcAdapter = NfcAdapter.getDefaultAdapter(this)
        
        setContent {
            viewModel = viewModel<CarrierViewModel>()
            CarrierApp(viewModel, carrierId, this)
        }
        
        // Connect to bridge
        viewModel.connectToBridge("ws://10.0.2.2:8765", carrierId) // 10.0.2.2 is localhost from Android emulator
    }
    
    override fun onResume() {
        super.onResume()
        enableNfcForegroundDispatch()
    }
    
    override fun onPause() {
        super.onPause()
        disableNfcForegroundDispatch()
    }
    
    override fun onNewIntent(intent: Intent) {
        super.onNewIntent(intent)
        
        if (NfcAdapter.ACTION_TAG_DISCOVERED == intent.action ||
            NfcAdapter.ACTION_NDEF_DISCOVERED == intent.action) {
            
            viewModel.selectedShipment.value?.let { shipment ->
                writeNfcTag(intent, shipment)
            }
        }
    }
    
    private fun enableNfcForegroundDispatch() {
        nfcAdapter?.let { adapter ->
            val intent = Intent(this, javaClass).apply {
                addFlags(Intent.FLAG_ACTIVITY_SINGLE_TOP)
            }
            val pendingIntent = PendingIntent.getActivity(
                this, 0, intent,
                PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_MUTABLE
            )
            
            val filters = arrayOf(
                IntentFilter(NfcAdapter.ACTION_TAG_DISCOVERED),
                IntentFilter(NfcAdapter.ACTION_NDEF_DISCOVERED)
            )
            
            adapter.enableForegroundDispatch(this, pendingIntent, filters, null)
        }
    }
    
    private fun disableNfcForegroundDispatch() {
        nfcAdapter?.disableForegroundDispatch(this)
    }
    
    private fun writeNfcTag(intent: Intent, shipment: ShipmentPayload) {
        val tag = intent.getParcelableExtra<Tag>(NfcAdapter.EXTRA_TAG) ?: return
        
        try {
            val ndef = Ndef.get(tag)
            if (ndef != null) {
                ndef.connect()
                
                // Create NDEF message with shipment data
                val gson = Gson()
                val payloadJson = gson.toJson(shipment)
                val ndefRecord = NdefRecord.createMime("application/vnd.logistics.shipment", payloadJson.toByteArray())
                val ndefMessage = NdefMessage(arrayOf(ndefRecord))
                
                ndef.writeNdefMessage(ndefMessage)
                ndef.close()
                
                // Send delivery data to receiver
                sendToReceiver(shipment)
                
                // Report delivery completion
                viewModel.reportDelivery(shipment.transaction.id)
                
                Toast.makeText(this, "Delivery completed successfully!", Toast.LENGTH_LONG).show()
            }
        } catch (e: Exception) {
            Log.e("NFC", "Error writing NFC tag", e)
            Toast.makeText(this, "Error: ${e.message}", Toast.LENGTH_LONG).show()
        }
    }
    
    private fun sendToReceiver(shipment: ShipmentPayload) {
        CoroutineScope(Dispatchers.IO).launch {
            try {
                val client = OkHttpClient()
                val gson = Gson()
                
                val requestBody = JSONObject().apply {
                    put("type", "nfc_delivery")
                    put("payload", JSONObject(gson.toJson(shipment)))
                }.toString().toRequestBody("application/json".toMediaType())
                
                val request = Request.Builder()
                    .url("http://10.0.2.2:65435") // Receiver NFC endpoint
                    .post(requestBody)
                    .build()
                
                client.newCall(request).execute().use { response ->
                    if (response.isSuccessful) {
                        Log.d("NFC", "Successfully sent to receiver")
                    } else {
                        Log.e("NFC", "Failed to send to receiver: ${response.code}")
                    }
                }
            } catch (e: Exception) {
                Log.e("NFC", "Error sending to receiver", e)
            }
        }
    }
}

@Composable
fun CarrierApp(viewModel: CarrierViewModel, carrierId: String, activity: ComponentActivity) {
    val isConnected by viewModel.isConnected
    val shipments = viewModel.shipments
    val selectedShipment by viewModel.selectedShipment
    
    MaterialTheme {
        Surface(
            modifier = Modifier.fillMaxSize(),
            color = MaterialTheme.colorScheme.background
        ) {
            Column(
                modifier = Modifier
                    .fillMaxSize()
                    .padding(16.dp)
            ) {
                // Header
                Card(
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(bottom = 16.dp),
                    colors = CardDefaults.cardColors(
                        containerColor = if (isConnected) Color(0xFF4CAF50) else Color(0xFFFF5252)
                    )
                ) {
                    Column(
                        modifier = Modifier.padding(16.dp)
                    ) {
                        Text(
                            text = "NFC Logistics Carrier",
                            fontSize = 24.sp,
                            fontWeight = FontWeight.Bold,
                            color = Color.White
                        )
                        Text(
                            text = "Carrier ID: $carrierId",
                            fontSize = 14.sp,
                            color = Color.White
                        )
                        Text(
                            text = if (isConnected) "Connected to Bridge" else "Disconnected",
                            fontSize = 16.sp,
                            color = Color.White
                        )
                    }
                }
                
                // Selected shipment for NFC
                selectedShipment?.let { shipment ->
                    Card(
                        modifier = Modifier
                            .fillMaxWidth()
                            .padding(bottom = 16.dp),
                        colors = CardDefaults.cardColors(
                            containerColor = Color(0xFF2196F3)
                        )
                    ) {
                        Column(
                            modifier = Modifier.padding(16.dp)
                        ) {
                            Text(
                                text = "Ready for NFC Delivery",
                                fontSize = 18.sp,
                                fontWeight = FontWeight.Bold,
                                color = Color.White
                            )
                            Text(
                                text = "Transaction: ${shipment.transaction.id}",
                                fontSize = 14.sp,
                                color = Color.White
                            )
                            Text(
                                text = "Tap NFC pad at receiver location",
                                fontSize = 16.sp,
                                color = Color.White
                            )
                        }
                    }
                }
                
                // Shipments list
                Text(
                    text = "Active Shipments",
                    fontSize = 20.sp,
                    fontWeight = FontWeight.Bold,
                    modifier = Modifier.padding(bottom = 8.dp)
                )
                
                LazyColumn {
                    items(shipments) { shipment ->
                        ShipmentCard(
                            shipment = shipment,
                            onSelect = {
                                viewModel.selectShipment(shipment)
                                viewModel.addToGoogleWallet(activity, shipment)
                            }
                        )
                    }
                }
            }
        }
    }
}

@Composable
fun ShipmentCard(shipment: ShipmentPayload, onSelect: () -> Unit) {
    Card(
        modifier = Modifier
            .fillMaxWidth()
            .padding(vertical = 4.dp),
        onClick = onSelect
    ) {
        Column(
            modifier = Modifier.padding(16.dp)
        ) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween
            ) {
                Text(
                    text = shipment.transaction.id,
                    fontWeight = FontWeight.Bold
                )
                Text(
                    text = shipment.transaction.status,
                    color = when (shipment.transaction.status) {
                        "initiated" -> Color(0xFFFF9800)
                        "in_transit" -> Color(0xFF2196F3)
                        "delivered" -> Color(0xFF4CAF50)
                        else -> Color.Gray
                    }
                )
            }
            
            Spacer(modifier = Modifier.height(8.dp))
            
            Text(text = "BOL: ${shipment.bol.number}")
            Text(text = "Invoice: ${shipment.commercial_invoice.number}")
            Text(text = "Value: ${shipment.commercial_invoice.currency} ${shipment.commercial_invoice.total_value}")
            Text(text = "Pallets: ${shipment.logistics.pallet_count}")
            Text(text = "Weight: ${shipment.packing_slip.total_weight} ${shipment.packing_slip.weight_unit}")
            
            Spacer(modifier = Modifier.height(8.dp))
            
            Row {
                Text(
                    text = "From: ${shipment.erp_identifiers.shipper.company_id}",
                    fontSize = 12.sp
                )
                Spacer(modifier = Modifier.width(16.dp))
                Text(
                    text = "To: ${shipment.erp_identifiers.receiver.company_id}",
                    fontSize = 12.sp
                )
            }
        }
    }
}