# ----- Connessione SSH dal Mac -----                                                 
ssh root@151.237.25.234 -p 24290                                                                                                              

# ----- Avvio backend (dentro la SSH) -----                                                                                                                 
  cd /workspace/ai-for-healthcare                                                                                                               
  git pull origin main                          # se hai pushato modifiche                                                                      
  source .venv/bin/activate                                                                                                                     
  pkill -f jupyter-noteboo 2>/dev/null          # libera porta 8080 se serve                                                                    
                                                                                                                                                
  export HF_TOKEN=$(grep ^HF_TOKEN .env | cut -d= -f2)                                                                                          
  export HF_HOME=/workspace/ai-for-healthcare/models                                                                                            
  export HF_HUB_ENABLE_HF_TRANSFER=1                                                                                                            
  export OCR_CACHE_FILE=/workspace/ai-for-healthcare/data/ocr_cache.txt                                                                         
                                                                                                                                              
  uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload      


# ----- Test che risponda -----                                                                                                                           
  curl http://151.237.25.234:23966/health     # dal Mac   


# ----- SSH Tunnel per Realtime STT (WhisperLive) -----                            
ssh -L 9090:localhost:9090 root@151.237.25.234 -p 24290                                                                                       

# ----- Test CUDA -----
python -c "import torch; print('CUDA:', torch.cuda.is_available(), torch.cuda.get_device_name(0) if torch.cuda.is_available() else '')"


# ----- Crescita in tempo reale (utile durante un download in corso) -----                                                                                  
  watch -n 2 'du -sh /workspace/ai-for-healthcare/models/hub/* 2>/dev/null'