package com.printpal.app;

import android.content.SharedPreferences;
import android.os.Bundle;
import android.view.View;
import android.widget.Button;
import android.widget.EditText;
import android.widget.TextView;

import androidx.appcompat.app.AppCompatActivity;

import java.net.HttpURLConnection;
import java.net.URL;

public class SettingsActivity extends AppCompatActivity {

    private static final String PREFS_NAME = "printpal_prefs";
    private static final String KEY_SERVER_URL = "server_url";

    private EditText urlInput;
    private TextView statusText;
    private Button saveButton;
    private Button testButton;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_settings);

        urlInput = findViewById(R.id.server_url_input);
        statusText = findViewById(R.id.status_text);
        saveButton = findViewById(R.id.save_button);
        testButton = findViewById(R.id.test_button);

        SharedPreferences prefs = getSharedPreferences(PREFS_NAME, MODE_PRIVATE);
        String savedUrl = prefs.getString(KEY_SERVER_URL, "");
        urlInput.setText(savedUrl);

        saveButton.setOnClickListener(v -> saveUrl());
        testButton.setOnClickListener(v -> testConnection());
    }

    private void saveUrl() {
        String url = urlInput.getText().toString().trim();
        if (url.isEmpty()) {
            statusText.setText("Enter a valid URL");
            statusText.setVisibility(View.VISIBLE);
            return;
        }
        if (!url.startsWith("http://") && !url.startsWith("https://")) {
            url = "http://" + url;
        }
        if (url.endsWith("/")) {
            url = url.substring(0, url.length() - 1);
        }

        SharedPreferences prefs = getSharedPreferences(PREFS_NAME, MODE_PRIVATE);
        prefs.edit().putString(KEY_SERVER_URL, url).apply();

        statusText.setText("Saved! Restarting...");
        statusText.setTextColor(0xFF2ECC71);
        statusText.setVisibility(View.VISIBLE);

        finish();
    }

    private void testConnection() {
        String url = urlInput.getText().toString().trim();
        if (url.isEmpty()) {
            statusText.setText("Enter a URL first");
            statusText.setVisibility(View.VISIBLE);
            return;
        }
        if (!url.startsWith("http://") && !url.startsWith("https://")) {
            url = "http://" + url;
        }

        statusText.setText("Testing...");
        statusText.setTextColor(0xFF8888A0);
        statusText.setVisibility(View.VISIBLE);
        saveButton.setEnabled(false);
        testButton.setEnabled(false);

        String finalUrl = url;
        new Thread(() -> {
            try {
                URL testUrl = new URL(finalUrl);
                HttpURLConnection conn = (HttpURLConnection) testUrl.openConnection();
                conn.setConnectTimeout(3000);
                conn.setReadTimeout(3000);
                int code = conn.getResponseCode();

                runOnUiThread(() -> {
                    if (code == 200) {
                        statusText.setText("Connected! (HTTP " + code + ")");
                        statusText.setTextColor(0xFF2ECC71);
                    } else {
                        statusText.setText("Server responded (HTTP " + code + ")");
                        statusText.setTextColor(0xFFF39C12);
                    }
                    statusText.setVisibility(View.VISIBLE);
                    saveButton.setEnabled(true);
                    testButton.setEnabled(true);
                });
            } catch (Exception e) {
                runOnUiThread(() -> {
                    statusText.setText("Cannot connect: " + e.getMessage());
                    statusText.setTextColor(0xFFE74C3C);
                    statusText.setVisibility(View.VISIBLE);
                    saveButton.setEnabled(true);
                    testButton.setEnabled(true);
                });
            }
        }).start();
    }
}
