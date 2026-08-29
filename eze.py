import torch

print("¿CUDA disponible?:", torch.cuda.is_available())

if torch.cuda.is_available():
    print("Nombre del dispositivo CUDA:", torch.cuda.get_device_name(0))
    print("Versión de CUDA usada por PyTorch:", torch.version.cuda)
else:
    print("⚠️ PyTorch no está usando CUDA.")
