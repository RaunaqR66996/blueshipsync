package com.nfclogistics.carrier

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
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.lifecycle.viewmodel.compose.viewModel
import com.google.android.gms.pay.PayClient
import com.google.android.gms.pay.Pay
import com.google.android.gms.wallet.*
import com.google.gson.Gson
import com.google.gson.reflect.TypeToken
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import org.json.JSONObject
import java.io.OutputStreamWriter
import java.net.HttpURLConnection
import java.net.URL
import java.nio.charset.Charset
import java.time.Instant
import java.time.ZoneOffset
import java.time.format.DateTimeFormatter

/**
 * NFC Logistics Carrier App - Main Activity
 * 
 * This activity handles NFC operations for the logistics carrier system,
 * including receiving shipment data from shippers and transmitting to receivers.
 * Integrates with Google Wallet for secure in-transit storage.
 */
class MainActivity : ComponentActivity() {
    
    companion object {
        private const val TAG = "NFCLogisticsCarrier"
        private const val BRIDGE_HOST = "10.0.2.2" // localhost for emulator
        private const val BRIDGE_PORT = 65432
        private const val WALLET_ENVIRONMENT = WalletConstants.ENVIRONMENT_TEST
    }
    
    private var nfcAdapter: NfcAdapter? = null
    private var pendingIntent: PendingIntent? = null
    private var intentFiltersArray: Array<IntentFilter>? = null
    private var techListsArray: Array<Array<String>>? = null
    private lateinit var paymentsClient: PaymentsClient
    private lateinit var payClient: PayClient
    
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        
        Log.d(TAG, "NFC Logistics Carrier App started")
        
        initializeNFC()
        initializeGoogleWallet()
        
        setContent {
            NFCLogisticsTheme {
                Surface(
                    modifier = Modifier.fillMaxSize(),
                    color = MaterialTheme.colorScheme.background
                ) {
                    CarrierMainScreen()
                }
            }
        }
    }
    
    private fun initializeNFC() {
        nfcAdapter = NfcAdapter.getDefaultAdapter(this)
        
        if (nfcAdapter == null) {
            Log.e(TAG, "NFC not supported on this device")
            Toast.makeText(this, "NFC not supported", Toast.LENGTH_LONG).show()
            return
        }
        
        if (!nfcAdapter!!.isEnabled) {
            Log.w(TAG, "NFC is disabled")
            Toast.makeText(this, "Please enable NFC", Toast.LENGTH_LONG).show()
        }
        
        // Setup NFC intent handling
        pendingIntent = PendingIntent.getActivity(
            this, 0,
            Intent(this, javaClass).addFlags(Intent.FLAG_ACTIVITY_SINGLE_TOP),
            PendingIntent.FLAG_MUTABLE
        )
        
        val ndefFilter = IntentFilter(NfcAdapter.ACTION_NDEF_DISCOVERED).apply {
            addDataType("application/json")
        }
        
        val tagFilter = IntentFilter(NfcAdapter.ACTION_TAG_DISCOVERED)
        intentFiltersArray = arrayOf(ndefFilter, tagFilter)
        
        techListsArray = arrayOf(
            arrayOf(Ndef::class.java.name)
        )
        
        Log.d(TAG, "NFC initialized successfully")
    }
    
    private fun initializeGoogleWallet() {
        val walletOptions = Wallet.WalletOptions.Builder()
            .setEnvironment(WALLET_ENVIRONMENT)
            .build()
        
        paymentsClient = Wallet.getPaymentsClient(this, walletOptions)
        payClient = Pay.getClient(this)
        
        Log.d(TAG, "Google Wallet initialized")
    }
    
    override fun onResume() {
        super.onResume()
        nfcAdapter?.enableForegroundDispatch(
            this, pendingIntent, intentFiltersArray, techListsArray
        )
        Log.d(TAG, "NFC foreground dispatch enabled")
    }
    
    override fun onPause() {
        super.onPause()
        nfcAdapter?.disableForegroundDispatch(this)
        Log.d(TAG, "NFC foreground dispatch disabled")
    }
    
    override fun onNewIntent(intent: Intent) {
        super.onNewIntent(intent)
        Log.d(TAG, "New NFC intent received: ${intent.action}")
        
        when (intent.action) {
            NfcAdapter.ACTION_NDEF_DISCOVERED,
            NfcAdapter.ACTION_TAG_DISCOVERED -> {
                handleNFCIntent(intent)
            }
        }
    }
    
    private fun handleNFCIntent(intent: Intent) {
        val tag: Tag? = intent.getParcelableExtra(NfcAdapter.EXTRA_TAG)
        
        tag?.let {
            Log.d(TAG, "NFC tag detected")
            
            // Check if this is a read or write operation based on context
            val viewModel: CarrierViewModel = CarrierViewModel()
            
            if (viewModel.hasActiveShipment()) {
                // Write mode - transmit to receiver
                writePayloadToNFC(it, viewModel.getActivePayload())
            } else {
                // Read mode - receive from shipper (or read existing data)
                readPayloadFromNFC(it)
            }
        }
    }
    
    private fun readPayloadFromNFC(tag: Tag) {
        try {
            val ndef = Ndef.get(tag)
            ndef?.connect()
            
            val ndefMessage = ndef?.ndefMessage
            ndefMessage?.let { message ->
                val records = message.records
                for (record in records) {
                    if (record.tnf == NdefRecord.TNF_MIME_MEDIA) {
                        val payload = String(record.payload, Charset.forName("UTF-8"))
                        Log.d(TAG, "Read NFC payload: $payload")
                        
                        try {
                            val gson = Gson()
                            val payloadType = object : TypeToken<Map<String, Any>>() {}.type
                            val payloadData: Map<String, Any> = gson.fromJson(payload, payloadType)
                            
                            processReceivedPayload(payloadData)
                        } catch (e: Exception) {
                            Log.e(TAG, "Failed to parse NFC payload", e)
                            showToast("Invalid payload format")
                        }
                    }
                }
            }
            
            ndef?.close()
        } catch (e: Exception) {
            Log.e(TAG, "Error reading NFC tag", e)
            showToast("Failed to read NFC tag")
        }
    }
    
    private fun writePayloadToNFC(tag: Tag, payload: Map<String, Any>) {
        try {
            val ndef = Ndef.get(tag)
            ndef?.connect()
            
            if (ndef?.isWritable == true) {
                val gson = Gson()
                val payloadJson = gson.toJson(payload)
                
                val mimeRecord = NdefRecord.createMime(
                    "application/json",
                    payloadJson.toByteArray(Charset.forName("UTF-8"))
                )
                
                val ndefMessage = NdefMessage(arrayOf(mimeRecord))
                
                ndef.writeNdefMessage(ndefMessage)
                Log.d(TAG, "Successfully wrote payload to NFC tag")
                showToast("Shipment data transmitted to receiver")
                
                // Update payload status and sync with bridge
                updatePayloadStatus(payload, "delivered")
                
            } else {
                Log.e(TAG, "NFC tag is not writable")
                showToast("Cannot write to this NFC tag")
            }
            
            ndef?.close()
        } catch (e: Exception) {
            Log.e(TAG, "Error writing to NFC tag", e)
            showToast("Failed to write to NFC tag")
        }
    }
    
    private fun processReceivedPayload(payload: Map<String, Any>) {
        Log.d(TAG, "Processing received payload: ${payload["transaction_id"]}")
        
        // Store in Google Wallet as an in-transit pass
        storeInGoogleWallet(payload)
        
        // Update status to in-transit
        updatePayloadStatus(payload, "in_transit")
        
        // Sync with bridge
        syncWithBridge(payload)
        
        showToast("Shipment received and stored securely")
    }
    
    private fun storeInGoogleWallet(payload: Map<String, Any>) {
        try {
            val transitObject = createTransitObject(payload)
            
            // Create save request
            val saveRequest = SavePassesRequest.newBuilder()
                .addTransitObject(transitObject)
                .build()
            
            paymentsClient.savePassesObject(saveRequest)
                .addOnSuccessListener {
                    Log.d(TAG, "Successfully saved transit pass to Google Wallet")
                }
                .addOnFailureListener { e ->
                    Log.e(TAG, "Failed to save to Google Wallet", e)
                }
        } catch (e: Exception) {
            Log.e(TAG, "Error creating Google Wallet pass", e)
        }
    }
    
    private fun createTransitObject(payload: Map<String, Any>): TransitObject {
        val transactionId = payload["transaction_id"] as? String ?: "UNKNOWN"
        val bolInfo = payload["bol"] as? Map<String, Any> ?: emptyMap()
        val packingSlip = payload["packing_slip"] as? Map<String, Any> ?: emptyMap()
        val commercialInvoice = payload["commercial_invoice"] as? Map<String, Any> ?: emptyMap()
        
        return TransitObject.newBuilder()
            .setId("nfc_logistics_$transactionId")
            .setClassId("nfc_logistics_class")
            .setState(State.ACTIVE)
            .setPassengerType(PassengerType.SINGLE)
            .setPassengerNames("Logistics Shipment")
            .setTripType(TripType.ONE_WAY)
            .setTicketLeg(
                TicketLeg.newBuilder()
                    .setOriginStationCode(bolInfo["origin"] as? String ?: "")
                    .setDestinationStationCode(bolInfo["destination"] as? String ?: "")
                    .setDepartureDateTime(getCurrentTimestamp())
                    .setArrivalDateTime(bolInfo["delivery_date"] as? String ?: "")
                    .build()
            )
            .setTextModulesData(
                mutableListOf(
                    TextModuleData.newBuilder()
                        .setHeader("Transaction ID")
                        .setBody(transactionId)
                        .build(),
                    TextModuleData.newBuilder()
                        .setHeader("BOL Number")
                        .setBody(bolInfo["number"] as? String ?: "")
                        .build(),
                    TextModuleData.newBuilder()
                        .setHeader("Total Weight")
                        .setBody("${packingSlip["total_weight"]} ${packingSlip["weight_unit"]}")
                        .build(),
                    TextModuleData.newBuilder()
                        .setHeader("Total Value")
                        .setBody("${commercialInvoice["currency"]} ${commercialInvoice["total_value"]}")
                        .build()
                )
            )
            .build()
    }
    
    private fun updatePayloadStatus(payload: Map<String, Any>, newStatus: String) {
        val mutablePayload = payload.toMutableMap()
        mutablePayload["status"] = newStatus
        mutablePayload["timestamp"] = getCurrentTimestamp()
        
        // Add audit trail entry
        val auditTrail = (mutablePayload["audit_trail"] as? MutableList<Map<String, Any>>) 
            ?: mutableListOf()
        
        auditTrail.add(mapOf(
            "action" to "status_updated_by_carrier",
            "timestamp" to getCurrentTimestamp(),
            "actor" to "carrier_app",
            "location" to "Mobile Device",
            "notes" to "Status updated to $newStatus via NFC app"
        ))
        
        mutablePayload["audit_trail"] = auditTrail
        
        Log.d(TAG, "Updated payload status to $newStatus")
    }
    
    private fun syncWithBridge(payload: Map<String, Any>) {
        // Sync payload data with the bridge server
        kotlinx.coroutines.GlobalScope.launch(Dispatchers.IO) {
            try {
                val url = URL("http://$BRIDGE_HOST:$BRIDGE_PORT/sync")
                val connection = url.openConnection() as HttpURLConnection
                
                connection.requestMethod = "POST"
                connection.setRequestProperty("Content-Type", "application/json")
                connection.doOutput = true
                
                val gson = Gson()
                val jsonPayload = gson.toJson(payload)
                
                OutputStreamWriter(connection.outputStream).use { writer ->
                    writer.write(jsonPayload)
                }
                
                val responseCode = connection.responseCode
                Log.d(TAG, "Bridge sync response: $responseCode")
                
                withContext(Dispatchers.Main) {
                    if (responseCode == 200) {
                        showToast("Synced with bridge successfully")
                    } else {
                        showToast("Failed to sync with bridge")
                    }
                }
                
            } catch (e: Exception) {
                Log.e(TAG, "Failed to sync with bridge", e)
                withContext(Dispatchers.Main) {
                    showToast("Bridge sync failed - operating offline")
                }
            }
        }
    }
    
    private fun getCurrentTimestamp(): String {
        return Instant.now()
            .atOffset(ZoneOffset.UTC)
            .format(DateTimeFormatter.ISO_INSTANT)
    }
    
    private fun showToast(message: String) {
        runOnUiThread {
            Toast.makeText(this, message, Toast.LENGTH_SHORT).show()
        }
    }
}

/**
 * Main Composable UI for the Carrier App
 */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun CarrierMainScreen(viewModel: CarrierViewModel = viewModel()) {
    var selectedTab by remember { mutableStateOf(0) }
    val tabs = listOf("Active Shipments", "NFC Operations", "History")
    
    Column(modifier = Modifier.fillMaxSize()) {
        // Top App Bar
        TopAppBar(
            title = {
                Text(
                    "NFC Logistics Carrier",
                    fontWeight = FontWeight.Bold
                )
            },
            colors = TopAppBarDefaults.topAppBarColors(
                containerColor = MaterialTheme.colorScheme.primary,
                titleContentColor = MaterialTheme.colorScheme.onPrimary
            )
        )
        
        // Tab Row
        TabRow(selectedTabIndex = selectedTab) {
            tabs.forEachIndexed { index, title ->
                Tab(
                    selected = selectedTab == index,
                    onClick = { selectedTab = index },
                    text = { Text(title) }
                )
            }
        }
        
        // Tab Content
        when (selectedTab) {
            0 -> ActiveShipmentsTab(viewModel)
            1 -> NFCOperationsTab(viewModel)
            2 -> HistoryTab(viewModel)
        }
    }
}

@Composable
fun ActiveShipmentsTab(viewModel: CarrierViewModel) {
    val activeShipments by viewModel.activeShipments.collectAsState()
    
    Column(
        modifier = Modifier
            .fillMaxSize()
            .padding(16.dp)
    ) {
        if (activeShipments.isEmpty()) {
            Box(
                modifier = Modifier.fillMaxSize(),
                contentAlignment = Alignment.Center
            ) {
                Column(horizontalAlignment = Alignment.CenterHorizontally) {
                    Icon(
                        Icons.Default.LocalShipping,
                        contentDescription = null,
                        modifier = Modifier.size(64.dp),
                        tint = Color.Gray
                    )
                    Spacer(modifier = Modifier.height(16.dp))
                    Text(
                        "No active shipments",
                        style = MaterialTheme.typography.headlineSmall,
                        color = Color.Gray
                    )
                    Text(
                        "Tap an NFC tag to receive shipment data",
                        style = MaterialTheme.typography.bodyMedium,
                        color = Color.Gray,
                        textAlign = TextAlign.Center
                    )
                }
            }
        } else {
            LazyColumn {
                items(activeShipments) { shipment ->
                    ShipmentCard(shipment = shipment, onClick = {
                        viewModel.selectShipment(shipment)
                    })
                    Spacer(modifier = Modifier.height(8.dp))
                }
            }
        }
    }
}

@Composable
fun NFCOperationsTab(viewModel: CarrierViewModel) {
    val context = LocalContext.current
    val nfcStatus by viewModel.nfcStatus.collectAsState()
    val selectedShipment by viewModel.selectedShipment.collectAsState()
    
    Column(
        modifier = Modifier
            .fillMaxSize()
            .padding(16.dp),
        horizontalAlignment = Alignment.CenterHorizontally
    ) {
        // NFC Status Card
        Card(
            modifier = Modifier.fillMaxWidth(),
            colors = CardDefaults.cardColors(
                containerColor = if (nfcStatus == "Ready") 
                    MaterialTheme.colorScheme.primaryContainer 
                else 
                    MaterialTheme.colorScheme.errorContainer
            )
        ) {
            Column(
                modifier = Modifier.padding(16.dp),
                horizontalAlignment = Alignment.CenterHorizontally
            ) {
                Icon(
                    Icons.Default.Nfc,
                    contentDescription = null,
                    modifier = Modifier.size(48.dp)
                )
                Spacer(modifier = Modifier.height(8.dp))
                Text(
                    "NFC Status: $nfcStatus",
                    style = MaterialTheme.typography.headlineSmall,
                    fontWeight = FontWeight.Bold
                )
            }
        }
        
        Spacer(modifier = Modifier.height(24.dp))
        
        // Operation Instructions
        if (selectedShipment != null) {
            Card(modifier = Modifier.fillMaxWidth()) {
                Column(modifier = Modifier.padding(16.dp)) {
                    Text(
                        "Ready to Deliver",
                        style = MaterialTheme.typography.headlineSmall,
                        fontWeight = FontWeight.Bold
                    )
                    Spacer(modifier = Modifier.height(8.dp))
                    Text(
                        "Tap the NFC pad at the delivery location to transmit shipment data to the receiver.",
                        style = MaterialTheme.typography.bodyMedium
                    )
                    Spacer(modifier = Modifier.height(16.dp))
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.spacedBy(8.dp)
                    ) {
                        Text("Transaction:", fontWeight = FontWeight.Bold)
                        Text(selectedShipment!!["transaction_id"] as? String ?: "Unknown")
                    }
                }
            }
        } else {
            Card(modifier = Modifier.fillMaxWidth()) {
                Column(modifier = Modifier.padding(16.dp)) {
                    Text(
                        "Ready to Receive",
                        style = MaterialTheme.typography.headlineSmall,
                        fontWeight = FontWeight.Bold
                    )
                    Spacer(modifier = Modifier.height(8.dp))
                    Text(
                        "Tap an NFC tag from the shipper to receive shipment data and store it securely in Google Wallet.",
                        style = MaterialTheme.typography.bodyMedium
                    )
                }
            }
        }
        
        Spacer(modifier = Modifier.height(24.dp))
        
        // Action Buttons
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.spacedBy(16.dp)
        ) {
            OutlinedButton(
                onClick = { viewModel.clearSelection() },
                modifier = Modifier.weight(1f),
                enabled = selectedShipment != null
            ) {
                Icon(Icons.Default.Clear, contentDescription = null)
                Spacer(modifier = Modifier.width(8.dp))
                Text("Clear")
            }
            
            Button(
                onClick = { 
                    Toast.makeText(context, "Hold device near NFC tag", Toast.LENGTH_SHORT).show()
                },
                modifier = Modifier.weight(1f)
            ) {
                Icon(Icons.Default.Nfc, contentDescription = null)
                Spacer(modifier = Modifier.width(8.dp))
                Text("Scan NFC")
            }
        }
    }
}

@Composable
fun HistoryTab(viewModel: CarrierViewModel) {
    val completedShipments by viewModel.completedShipments.collectAsState()
    
    Column(
        modifier = Modifier
            .fillMaxSize()
            .padding(16.dp)
    ) {
        if (completedShipments.isEmpty()) {
            Box(
                modifier = Modifier.fillMaxSize(),
                contentAlignment = Alignment.Center
            ) {
                Column(horizontalAlignment = Alignment.CenterHorizontally) {
                    Icon(
                        Icons.Default.History,
                        contentDescription = null,
                        modifier = Modifier.size(64.dp),
                        tint = Color.Gray
                    )
                    Spacer(modifier = Modifier.height(16.dp))
                    Text(
                        "No completed shipments",
                        style = MaterialTheme.typography.headlineSmall,
                        color = Color.Gray
                    )
                }
            }
        } else {
            LazyColumn {
                items(completedShipments) { shipment ->
                    HistoryShipmentCard(shipment = shipment)
                    Spacer(modifier = Modifier.height(8.dp))
                }
            }
        }
    }
}

@Composable
fun ShipmentCard(
    shipment: Map<String, Any>,
    onClick: () -> Unit
) {
    Card(
        modifier = Modifier
            .fillMaxWidth()
            .padding(vertical = 4.dp),
        onClick = onClick
    ) {
        Column(modifier = Modifier.padding(16.dp)) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween
            ) {
                Text(
                    shipment["transaction_id"] as? String ?: "Unknown",
                    style = MaterialTheme.typography.headlineSmall,
                    fontWeight = FontWeight.Bold
                )
                Text(
                    shipment["status"] as? String ?: "Unknown",
                    style = MaterialTheme.typography.bodyMedium,
                    color = MaterialTheme.colorScheme.primary
                )
            }
            
            Spacer(modifier = Modifier.height(8.dp))
            
            val bol = shipment["bol"] as? Map<String, Any>
            bol?.let {
                Text("BOL: ${it["number"]}", style = MaterialTheme.typography.bodyMedium)
                Text("Origin: ${it["origin"]}", style = MaterialTheme.typography.bodyMedium)
                Text("Destination: ${it["destination"]}", style = MaterialTheme.typography.bodyMedium)
            }
        }
    }
}

@Composable
fun HistoryShipmentCard(shipment: Map<String, Any>) {
    Card(
        modifier = Modifier
            .fillMaxWidth()
            .padding(vertical = 4.dp)
    ) {
        Column(modifier = Modifier.padding(16.dp)) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween
            ) {
                Text(
                    shipment["transaction_id"] as? String ?: "Unknown",
                    style = MaterialTheme.typography.titleMedium,
                    fontWeight = FontWeight.Bold
                )
                Icon(
                    Icons.Default.CheckCircle,
                    contentDescription = "Completed",
                    tint = Color.Green
                )
            }
            
            Spacer(modifier = Modifier.height(4.dp))
            
            Text(
                "Completed: ${shipment["completion_date"]}",
                style = MaterialTheme.typography.bodyMedium,
                color = Color.Gray
            )
        }
    }
}