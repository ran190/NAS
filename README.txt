Avant de lancer notre code principal codeNAS.py, il faut définir la topologie du réseau dans reseau.json.

Ensuite pour avoir directement la réécriture des fichiers de config des routeur, il faut donner le chemin du dossier dynamips contenant les cfg des routeurs dans la variable path dans le main de codeNAS.py
IL faut aussi définir le numéro du routeur dans le nom du fichier cfg à la fin de reseau.json.
Par exemple, pour "i8_startup-config" il faut mette le chiffre 8.
