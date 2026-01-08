"""
Plaid Link component
"""
import streamlit.components.v1 as components

def simple_plaid_link_button(link_token: str):
    """Display Plaid Link button"""
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <script src="https://cdn.plaid.com/link/v2/stable/link-initialize.js"></script>
        <style>
            body {{ margin: 0; padding: 20px; font-family: sans-serif; }}
            button {{ 
                background: #00D4AA; 
                color: white; 
                border: none; 
                padding: 15px 30px; 
                font-size: 16px; 
                border-radius: 8px; 
                cursor: pointer; 
                width: 100%; 
            }}
            button:hover {{ background: #00B894; }}
            .info {{ margin-top: 15px; padding: 10px; background: #d1ecf1; border-radius: 5px; }}
            .success {{ background: #d4edda; color: #155724; }}
            .token-box {{ 
                margin-top: 15px; 
                padding: 10px; 
                background: #f8f9fa; 
                border: 1px solid #ddd; 
                border-radius: 5px; 
                font-family: monospace; 
                font-size: 12px; 
                word-break: break-all;
                display: none;
            }}
        </style>
    </head>
    <body>
        <button id="btn">🏦 Connect Your Bank</button>
        <div id="msg" class="info">Click button above to connect</div>
        <div id="token-box" class="token-box">
            <b>Public Token:</b><br>
            <span id="token"></span><br>
            <b>Bank:</b> <span id="bank"></span><br>
            <button onclick="copyToken()" style="margin-top:10px; padding:8px; font-size:12px;">Copy Token</button>
        </div>

        <script>
            const TOKEN = "{link_token}";
            let pubToken = "";
            
            function copyToken() {{
                navigator.clipboard.writeText(pubToken);
                alert('Copied!');
            }}
            
            console.log("Token loaded:", TOKEN.substring(0, 30));
            
            const handler = Plaid.create({{
                token: TOKEN,
                onSuccess: (public_token, metadata) => {{
                    console.log("SUCCESS!", metadata.institution.name);
                    pubToken = public_token;
                    document.getElementById('msg').className = 'info success';
                    document.getElementById('msg').textContent = '✅ Connected to ' + metadata.institution.name;
                    document.getElementById('token').textContent = public_token;
                    document.getElementById('bank').textContent = metadata.institution.name;
                    document.getElementById('token-box').style.display = 'block';
                }},
                onExit: (err) => {{
                    if (err) console.error(err);
                    document.getElementById('msg').textContent = err ? 'Error: ' + err.display_message : 'Cancelled';
                }}
            }});
            
            document.getElementById('btn').onclick = () => handler.open();
        </script>
    </body>
    </html>
    """
    
    components.html(html, height=400)
