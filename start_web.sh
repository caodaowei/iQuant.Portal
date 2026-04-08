#!/bin/bash
# iQuant Web 服务启动脚本

cd /root/.openclaw/workspace/iquant

export PYTHONPATH=/root/.openclaw/workspace/iquant:$PYTHONPATH

python3 -c "
import sys
sys.path.insert(0, '.')
from web.app import create_app
app = create_app()
print('Starting iQuant Web Server on port 5000...')
print('Access: http://10.3.0.9:5000')
app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)
"
