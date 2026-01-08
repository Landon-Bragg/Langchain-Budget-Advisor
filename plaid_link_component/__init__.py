"""
Streamlit component for Plaid Link
"""
import streamlit.components.v1 as components

# Embed HTML directly to avoid path issues
PLAID_LINK_HTML = """
<!DOCTYPE html>
<html>
<head>
    <script src="https://cdn.plaid.com/link/v2/stable/link-initialize.js"></script>
    <style>
        body {
            margin: 0;
            padding: 0;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
        }
        .container {
            padding: 20px;
        }
        #plaid-button {
            background: #00D4AA;
            color: white;
            border: none;
            padding: 14px 28px;
            font-size: 16px;
            font-weight: 600;
            border-radius: 8px;
            cursor: pointer;
            width: 100%;
            transition: all 0.2s;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        #plaid-button:hover {
            background: #00B894;
            transform: translateY(-1px);
            box-shadow: 0 4px 8px rgba(0,0,0,0.15);
        }
        #plaid-button:disabled {
            background: #ccc;
            cursor: not-allowed;
        }
        .status {
            margin-top: 15px;
            padding: 12px;
            border-radius: 6px;
            font-size: 14px;
            display: none;
        }
        .status.success {
            background: #d4edda;
            color: #155724;
            border: 1px solid #c3e6cb;
            display: block;
        }
        .status.error {
            background: #f8d7da;
            color: #721c24;
            border: 1px solid #f5c6cb;
            display: block;
        }
        .status.info {
            background: #d1ecf1;
            color: #0c5460;
            border: 1px solid #bee5eb;
            display: block;
        }
        .token-display {
            margin-top: 15px;
            padding: 12px;
            background: #f8f9fa;
            border: 1px solid #dee2e6;
            border-radius: 6px;
            font-family: monospace;
            font-size: 12px;
            word-break: break-all;
            display: none;
        }
        .token-display.show {
            display: block;
        }
        .copy-button {
            margin-top: 8px;
            background: #007bff;
            color: white;
            border: none;
            padding: 6px 12px;
            border-radius: 4px;
            cursor: pointer;
            font-size: 12px;
        }
        .copy-button:hover {
            background: #0056b3;
        }
    </style>
</head>
<body>
    <div class="container">
        <button id="plaid-button">🏦 Connect Your Bank Account</button>
        <div id="status" class="status"></div>
        <div id="token-display" class="token-display">
            <strong>Public Token:</strong><br>
            <span id="token-value"></span><br>
            <button class="copy-button" onclick="copyToken()">Copy Token</button>
            <br><br>
            <strong>Institution:</strong> <span id="institution-name"></span><br>
            <br>
            <small>ℹ️ Copy this token and use "Manual Token Exchange" below to complete the connection.</small>
        </div>
    </div>

    <script>
        const LINK_TOKEN = "{{LINK_TOKEN}}";
        const button = document.getElementById('plaid-button');
        const statusDiv = document.getElementById('status');
        const tokenDisplay = document.getElementById('token-display');
        const tokenValue = document.getElementById('token-value');
        const institutionNameSpan = document.getElementById('institution-name');

        let publicToken = null;
        let institutionName = null;

        function showStatus(message, type) {
            statusDiv.textContent = message;
            statusDiv.className = 'status ' + type;
        }

        function copyToken() {
            navigator.clipboard.writeText(publicToken).then(() => {
                alert('✅ Token copied to clipboard!');
            }).catch(() => {
                const textArea = document.createElement('textarea');
                textArea.value = publicToken;
                document.body.appendChild(textArea);
                textArea.select();
                document.execCommand('copy');
                document.body.removeChild(textArea);
                alert('✅ Token copied to clipboard!');
            });
        }

        console.log('Plaid Link Token received:', LINK_TOKEN.substring(0, 20) + '...');

        if (!LINK_TOKEN || LINK_TOKEN === "{{LINK_TOKEN}}" || LINK_TOKEN.length < 10) {
            showStatus('⚠️ Error: Link token not loaded properly', 'error');
            button.disabled = true;
        } else if (!LINK_TOKEN.startsWith('link-')) {
            showStatus('⚠️ Error: Invalid link token format', 'error');
            button.disabled = true;
        } else {
            showStatus('✅ Ready! Click the button to connect your bank.', 'info');
            
            try {
                const handler = Plaid.create({
                    token: LINK_TOKEN,
                    onSuccess: function(public_token, metadata) {
                        console.log('✅ Success!', metadata.institution.name);
                        
                        publicToken = public_token;
                        institutionName = metadata.institution.name;
                        
                        showStatus('✅ Connected to ' + metadata.institution.name + '!', 'success');
                        
                        tokenValue.textContent = public_token;
                        institutionNameSpan.textContent = metadata.institution.name;
                        tokenDisplay.className = 'token-display show';
                        
                        button.textContent = '✅ Connected to ' + metadata.institution.name;
                        button.disabled = true;
                    },
                    onExit: function(err, metadata) {
                        if (err) {
                            console.error('Error:', err);
                            showStatus('❌ ' + (err.display_message || 'Connection failed'), 'error');
                        } else {
                            showStatus('Connection cancelled. Click to try again.', 'info');
                        }
                    },
                    onLoad: function() {
                        console.log('Plaid Link loaded');
                    }
                });

                button.onclick = function() {
                    console.log('Opening Plaid Link...');
                    showStatus('Opening bank login...', 'info');
                    handler.open();
                };
            } catch (error) {
                console.error('Error initializing Plaid:', error);
                showStatus('❌ Error: ' + error.message, 'error');
            }
        }
    </script>
</body>
</html>
"""

def simple_plaid_link_button(link_token: str):
    """
    Display Plaid Link button
    Shows the token after connection for manual exchange
    """
    # Inject the link token into the HTML
    html_with_token = PLAID_LINK_HTML.replace('{{LINK_TOKEN}}', link_token)
    
    # Display with height to show token display
    components.html(html_with_token, height=350, scrolling=False)