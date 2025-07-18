package com.example.bluechipsync

import android.app.PendingIntent
import android.content.Intent
import android.nfc.NdefMessage
import android.nfc.NdefRecord
import android.nfc.NfcAdapter
import android.nfc.NfcEvent
import android.os.Bundle
import androidx.appcompat.app.AppCompatActivity
import android.util.Base64
import android.util.Log
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import org.json.JSONObject
import java.net.HttpURLConnection
import java.net.URL
import java.nio.charset.Charset

class MainActivity : AppCompatActivity(), NfcAdapter.CreateNdefMessageCallback {

    private val scope = CoroutineScope(Dispatchers.IO)
    private lateinit var nfcAdapter: NfcAdapter
    private var currentPayload: JSONObject? = null

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)

        nfcAdapter = NfcAdapter.getDefaultAdapter(this)
        nfcAdapter.setNdefPushMessageCallback(this, this)

        // The transaction ID could be passed via deep link / push notification
        val txId = intent.getStringExtra("TX_ID") ?: "TX-PLACEHOLDER"
        fetchPayloadFromBridge(txId)
    }

    private fun fetchPayloadFromBridge(txId: String) {
        scope.launch {
            try {
                // 10.0.2.2 routes to host machine in Android emulator; adjust for production
                val url = URL("http://10.0.2.2:5000/payloads/$txId")
                val conn = url.openConnection() as HttpURLConnection
                conn.requestMethod = "GET"
                conn.connectTimeout = 5000
                conn.readTimeout = 5000
                conn.connect()

                if (conn.responseCode == 200) {
                    val response = conn.inputStream.bufferedReader().use { it.readText() }
                    currentPayload = JSONObject(response)
                    // TODO: Store in Google Wallet using Passes API
                    Log.i("CarrierApp", "Fetched payload $txId")
                } else {
                    Log.e("CarrierApp", "Failed to fetch payload: ${conn.responseCode}")
                }
            } catch (e: Exception) {
                Log.e("CarrierApp", "Error fetching payload", e)
            }
        }
    }

    override fun createNdefMessage(event: NfcEvent?): NdefMessage? {
        currentPayload?.let {
            val payloadBytes = it.toString().toByteArray(Charset.forName("UTF-8"))
            val record = NdefRecord.createMime("application/json", payloadBytes)
            return NdefMessage(arrayOf(record))
        }
        return null
    }

    override fun onResume() {
        super.onResume()
        val intent = Intent(this, javaClass).apply {
            flags = Intent.FLAG_ACTIVITY_SINGLE_TOP
        }
        val pendingIntent = PendingIntent.getActivity(this, 0, intent, PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE)
        nfcAdapter.enableForegroundDispatch(this, pendingIntent, null, null)
    }

    override fun onPause() {
        super.onPause()
        nfcAdapter.disableForegroundDispatch(this)
    }
}