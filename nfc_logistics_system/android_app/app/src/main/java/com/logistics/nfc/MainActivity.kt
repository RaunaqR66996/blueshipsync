package com.logistics.nfc

import android.Manifest
import android.app.PendingIntent
import android.content.Intent
import android.content.IntentFilter
import android.content.pm.PackageManager
import android.location.Location
import android.nfc.NdefMessage
import android.nfc.NdefRecord
import android.nfc.NfcAdapter
import android.nfc.Tag
import android.nfc.tech.Ndef
import android.os.Bundle
import android.util.Log
import android.widget.Toast
import androidx.activity.result.contract.ActivityResultContracts
import androidx.appcompat.app.AppCompatActivity
import androidx.core.app.ActivityCompat
import androidx.core.content.ContextCompat
import androidx.lifecycle.lifecycleScope
import com.google.android.gms.location.FusedLocationProviderClient
import com.google.android.gms.location.LocationServices
import com.google.android.gms.wallet.PaymentsClient
import com.google.android.gms.wallet.Wallet
import com.google.android.gms.wallet.WalletConstants
import com.logistics.nfc.databinding.ActivityMainBinding
import com.logistics.nfc.model.ShipmentPayload
import com.logistics.nfc.network.NetworkManager
import com.logistics.nfc.service.NFCService
import com.logistics.nfc.util.NFCUtil
import com.logistics.nfc.util.WalletUtil
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import org.json.JSONObject
import java.io.IOException
import java.nio.charset.StandardCharsets

class MainActivity : AppCompatActivity() {
    
    companion object {
        private const val TAG = "MainActivity"
        private const val LOCATION_PERMISSION_REQUEST_CODE = 1001
        private const val NFC_PERMISSION_REQUEST_CODE = 1002
    }
    
    private lateinit var binding: ActivityMainBinding
    private lateinit var nfcAdapter: NfcAdapter
    private lateinit var pendingIntent: PendingIntent
    private lateinit var fusedLocationClient: FusedLocationProviderClient
    private lateinit var paymentsClient: PaymentsClient
    private lateinit var networkManager: NetworkManager
    private lateinit var nfcUtil: NFCUtil
    private lateinit var walletUtil: WalletUtil
    
    private var currentLocation: Location? = null
    private var currentPayload: ShipmentPayload? = null
    private var isNFCEnabled = false
    
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityMainBinding.inflate(layoutInflater)
        setContentView(binding.root)
        
        initializeComponents()
        setupUI()
        checkPermissions()
        handleIntent(intent)
    }
    
    private fun initializeComponents() {
        // Initialize NFC
        nfcAdapter = NfcAdapter.getDefaultAdapter(this)
        pendingIntent = PendingIntent.getActivity(
            this, 0,
            Intent(this, javaClass).addFlags(Intent.FLAG_ACTIVITY_SINGLE_TOP),
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_MUTABLE
        )
        
        // Initialize location services
        fusedLocationClient = LocationServices.getFusedLocationProviderClient(this)
        
        // Initialize Google Wallet
        val walletOptions = Wallet.WalletOptions.Builder()
            .setEnvironment(WalletConstants.ENVIRONMENT_TEST)
            .build()
        paymentsClient = Wallet.getPaymentsClient(this, walletOptions)
        
        // Initialize network manager
        networkManager = NetworkManager()
        
        // Initialize utilities
        nfcUtil = NFCUtil()
        walletUtil = WalletUtil(paymentsClient)
    }
    
    private fun setupUI() {
        binding.apply {
            // Setup buttons
            btnConnectShipper.setOnClickListener { connectToShipper() }
            btnConnectReceiver.setOnClickListener { connectToReceiver() }
            btnReadNFC.setOnClickListener { enableNFCReading() }
            btnWriteNFC.setOnClickListener { enableNFCWriting() }
            btnSaveToWallet.setOnClickListener { saveToGoogleWallet() }
            btnSyncPayload.setOnClickListener { syncPayloadWithBridge() }
            
            // Setup status indicators
            updateNFCStatus()
            updateLocationStatus()
            updateConnectionStatus()
        }
    }
    
    private fun checkPermissions() {
        // Check location permissions
        if (ContextCompat.checkSelfPermission(
                this,
                Manifest.permission.ACCESS_FINE_LOCATION
            ) != PackageManager.PERMISSION_GRANTED
        ) {
            ActivityCompat.requestPermissions(
                this,
                arrayOf(
                    Manifest.permission.ACCESS_FINE_LOCATION,
                    Manifest.permission.ACCESS_COARSE_LOCATION
                ),
                LOCATION_PERMISSION_REQUEST_CODE
            )
        } else {
            getCurrentLocation()
        }
        
        // Check NFC availability
        if (nfcAdapter == null) {
            Toast.makeText(this, "NFC is not available on this device", Toast.LENGTH_LONG).show()
            binding.btnReadNFC.isEnabled = false
            binding.btnWriteNFC.isEnabled = false
        } else if (!nfcAdapter.isEnabled) {
            Toast.makeText(this, "Please enable NFC", Toast.LENGTH_LONG).show()
            binding.btnReadNFC.isEnabled = false
            binding.btnWriteNFC.isEnabled = false
        }
    }
    
    private fun getCurrentLocation() {
        if (ActivityCompat.checkSelfPermission(
                this,
                Manifest.permission.ACCESS_FINE_LOCATION
            ) == PackageManager.PERMISSION_GRANTED
        ) {
            fusedLocationClient.lastLocation.addOnSuccessListener { location ->
                currentLocation = location
                updateLocationStatus()
                Log.d(TAG, "Location updated: ${location?.latitude}, ${location?.longitude}")
            }
        }
    }
    
    private fun connectToShipper() {
        lifecycleScope.launch {
            try {
                binding.tvStatus.text = "Connecting to shipper..."
                val response = networkManager.connectToShipper()
                if (response.isSuccessful) {
                    binding.tvStatus.text = "Connected to shipper"
                    binding.btnConnectShipper.isEnabled = false
                    binding.btnConnectShipper.text = "Connected"
                    Toast.makeText(this@MainActivity, "Connected to shipper", Toast.LENGTH_SHORT).show()
                } else {
                    binding.tvStatus.text = "Failed to connect to shipper"
                    Toast.makeText(this@MainActivity, "Connection failed", Toast.LENGTH_SHORT).show()
                }
            } catch (e: Exception) {
                Log.e(TAG, "Error connecting to shipper", e)
                binding.tvStatus.text = "Connection error"
                Toast.makeText(this@MainActivity, "Connection error: ${e.message}", Toast.LENGTH_SHORT).show()
            }
        }
    }
    
    private fun connectToReceiver() {
        lifecycleScope.launch {
            try {
                binding.tvStatus.text = "Connecting to receiver..."
                val response = networkManager.connectToReceiver()
                if (response.isSuccessful) {
                    binding.tvStatus.text = "Connected to receiver"
                    binding.btnConnectReceiver.isEnabled = false
                    binding.btnConnectReceiver.text = "Connected"
                    Toast.makeText(this@MainActivity, "Connected to receiver", Toast.LENGTH_SHORT).show()
                } else {
                    binding.tvStatus.text = "Failed to connect to receiver"
                    Toast.makeText(this@MainActivity, "Connection failed", Toast.LENGTH_SHORT).show()
                }
            } catch (e: Exception) {
                Log.e(TAG, "Error connecting to receiver", e)
                binding.tvStatus.text = "Connection error"
                Toast.makeText(this@MainActivity, "Connection error: ${e.message}", Toast.LENGTH_SHORT).show()
            }
        }
    }
    
    private fun enableNFCReading() {
        isNFCEnabled = true
        binding.tvStatus.text = "NFC Reading enabled - Tap to read"
        binding.btnReadNFC.isEnabled = false
        binding.btnWriteNFC.isEnabled = true
        Toast.makeText(this, "NFC Reading enabled", Toast.LENGTH_SHORT).show()
    }
    
    private fun enableNFCWriting() {
        isNFCEnabled = true
        binding.tvStatus.text = "NFC Writing enabled - Tap to write"
        binding.btnReadNFC.isEnabled = true
        binding.btnWriteNFC.isEnabled = false
        Toast.makeText(this, "NFC Writing enabled", Toast.LENGTH_SHORT).show()
    }
    
    private fun saveToGoogleWallet() {
        currentPayload?.let { payload ->
            lifecycleScope.launch {
                try {
                    binding.tvStatus.text = "Saving to Google Wallet..."
                    val success = walletUtil.saveShipmentToWallet(payload)
                    if (success) {
                        binding.tvStatus.text = "Saved to Google Wallet"
                        Toast.makeText(this@MainActivity, "Saved to Google Wallet", Toast.LENGTH_SHORT).show()
                    } else {
                        binding.tvStatus.text = "Failed to save to Google Wallet"
                        Toast.makeText(this@MainActivity, "Failed to save to wallet", Toast.LENGTH_SHORT).show()
                    }
                } catch (e: Exception) {
                    Log.e(TAG, "Error saving to Google Wallet", e)
                    binding.tvStatus.text = "Wallet save error"
                    Toast.makeText(this@MainActivity, "Wallet error: ${e.message}", Toast.LENGTH_SHORT).show()
                }
            }
        } ?: run {
            Toast.makeText(this, "No payload to save", Toast.LENGTH_SHORT).show()
        }
    }
    
    private fun syncPayloadWithBridge() {
        currentPayload?.let { payload ->
            lifecycleScope.launch {
                try {
                    binding.tvStatus.text = "Syncing with bridge..."
                    val response = networkManager.syncPayloadWithBridge(payload)
                    if (response.isSuccessful) {
                        binding.tvStatus.text = "Payload synced successfully"
                        Toast.makeText(this@MainActivity, "Payload synced", Toast.LENGTH_SHORT).show()
                    } else {
                        binding.tvStatus.text = "Sync failed"
                        Toast.makeText(this@MainActivity, "Sync failed", Toast.LENGTH_SHORT).show()
                    }
                } catch (e: Exception) {
                    Log.e(TAG, "Error syncing payload", e)
                    binding.tvStatus.text = "Sync error"
                    Toast.makeText(this@MainActivity, "Sync error: ${e.message}", Toast.LENGTH_SHORT).show()
                }
            }
        } ?: run {
            Toast.makeText(this, "No payload to sync", Toast.LENGTH_SHORT).show()
        }
    }
    
    override fun onResume() {
        super.onResume()
        if (nfcAdapter != null && isNFCEnabled) {
            nfcAdapter.enableForegroundDispatch(this, pendingIntent, null, null)
        }
    }
    
    override fun onPause() {
        super.onPause()
        if (nfcAdapter != null) {
            nfcAdapter.disableForegroundDispatch(this)
        }
    }
    
    override fun onNewIntent(intent: Intent) {
        super.onNewIntent(intent)
        handleIntent(intent)
    }
    
    private fun handleIntent(intent: Intent) {
        when (intent.action) {
            NfcAdapter.ACTION_TAG_DISCOVERED,
            NfcAdapter.ACTION_TECH_DISCOVERED,
            NfcAdapter.ACTION_NDEF_DISCOVERED -> {
                val tag: Tag? = intent.getParcelableExtra(NfcAdapter.EXTRA_TAG)
                tag?.let { handleNFCTag(it) }
            }
        }
    }
    
    private fun handleNFCTag(tag: Tag) {
        lifecycleScope.launch {
            try {
                val ndef = Ndef.get(tag)
                if (ndef != null) {
                    if (binding.btnReadNFC.isEnabled.not()) {
                        // Reading mode
                        val payload = readNFCPayload(ndef)
                        if (payload != null) {
                            currentPayload = payload
                            updatePayloadDisplay(payload)
                            binding.tvStatus.text = "Payload read successfully"
                            Toast.makeText(this@MainActivity, "Payload read", Toast.LENGTH_SHORT).show()
                        } else {
                            binding.tvStatus.text = "Failed to read payload"
                            Toast.makeText(this@MainActivity, "Read failed", Toast.LENGTH_SHORT).show()
                        }
                    } else {
                        // Writing mode
                        currentPayload?.let { payload ->
                            val success = writeNFCPayload(ndef, payload)
                            if (success) {
                                binding.tvStatus.text = "Payload written successfully"
                                Toast.makeText(this@MainActivity, "Payload written", Toast.LENGTH_SHORT).show()
                            } else {
                                binding.tvStatus.text = "Failed to write payload"
                                Toast.makeText(this@MainActivity, "Write failed", Toast.LENGTH_SHORT).show()
                            }
                        } ?: run {
                            Toast.makeText(this@MainActivity, "No payload to write", Toast.LENGTH_SHORT).show()
                        }
                    }
                } else {
                    Toast.makeText(this@MainActivity, "NFC tag not supported", Toast.LENGTH_SHORT).show()
                }
            } catch (e: Exception) {
                Log.e(TAG, "Error handling NFC tag", e)
                Toast.makeText(this@MainActivity, "NFC error: ${e.message}", Toast.LENGTH_SHORT).show()
            }
        }
    }
    
    private suspend fun readNFCPayload(ndef: Ndef): ShipmentPayload? = withContext(Dispatchers.IO) {
        try {
            ndef.connect()
            val ndefMessage = ndef.cachedNdefMessage ?: ndef.readNdefMessage()
            val records = ndefMessage.records
            
            for (record in records) {
                if (record.toMimeType() == "application/vnd.logistics.shipment") {
                    val payloadString = String(record.payload, StandardCharsets.UTF_8)
                    return@withContext ShipmentPayload.fromJson(payloadString)
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
    
    private suspend fun writeNFCPayload(ndef: Ndef, payload: ShipmentPayload): Boolean = withContext(Dispatchers.IO) {
        try {
            ndef.connect()
            
            val payloadJson = payload.toJson()
            val payloadBytes = payloadJson.toByteArray(StandardCharsets.UTF_8)
            
            val record = NdefRecord.createMime("application/vnd.logistics.shipment", payloadBytes)
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
    
    private fun updatePayloadDisplay(payload: ShipmentPayload) {
        binding.apply {
            tvTransactionId.text = "Transaction: ${payload.transaction.transactionId}"
            tvBolNumber.text = "BOL: ${payload.billOfLading.bolNumber}"
            tvStatus.text = "Status: ${payload.transaction.status}"
            tvItems.text = "Items: ${payload.packingSlip.totalItems}"
            tvWeight.text = "Weight: ${payload.packingSlip.totalWeight} kg"
        }
    }
    
    private fun updateNFCStatus() {
        val isAvailable = nfcAdapter != null && nfcAdapter.isEnabled
        binding.tvNfcStatus.text = if (isAvailable) "NFC: Available" else "NFC: Not Available"
        binding.btnReadNFC.isEnabled = isAvailable
        binding.btnWriteNFC.isEnabled = isAvailable
    }
    
    private fun updateLocationStatus() {
        currentLocation?.let { location ->
            binding.tvLocationStatus.text = "Location: ${location.latitude}, ${location.longitude}"
        } ?: run {
            binding.tvLocationStatus.text = "Location: Not available"
        }
    }
    
    private fun updateConnectionStatus() {
        // This would be updated based on actual connection status
        binding.tvConnectionStatus.text = "Connections: Ready"
    }
    
    override fun onRequestPermissionsResult(
        requestCode: Int,
        permissions: Array<out String>,
        grantResults: IntArray
    ) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults)
        
        when (requestCode) {
            LOCATION_PERMISSION_REQUEST_CODE -> {
                if (grantResults.isNotEmpty() && grantResults[0] == PackageManager.PERMISSION_GRANTED) {
                    getCurrentLocation()
                } else {
                    Toast.makeText(this, "Location permission required", Toast.LENGTH_LONG).show()
                }
            }
        }
    }
}