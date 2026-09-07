import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).parents[1]))

from tools.catalogo import buscar_productos


def producto(item_id, codigo, nombre, categoria, subcategoria, marca="Marca"):
    return {
        "item_id": item_id,
        "codigo": codigo,
        "item_desc_0": nombre,
        "item_desc_1": "",
        "categoria": categoria,
        "subcategoria": subcategoria,
        "marca": marca,
        "precioNeto_USD": 100,
        "stock_mdp": 1,
        "stock_caba": 2,
    }


CATALOGO = [
    producto("m1", "M1", "Monitor gamer 24 pulgadas", "Monitores", "Monitor"),
    producto("n1", "N1", "Notebook Ryzen 5", "Notebooks", "Notebook"),
    producto("c1", "C1", "AMD Ryzen 5 5600G", "Procesadores", "CPU"),
    producto("g1", "G1", "Placa de video AMD Radeon RX 7600", "Placas de video", "GPU"),
    producto("s1", "S1", "Memoria Micro SD 128GB", "Memorias", "Memoria SD"),
    producto("r1", "R1", "Memoria RAM DDR5 16GB", "Memorias", "Memoria"),
]


class CatalogoTest(unittest.TestCase):
    def skus(self, consulta):
        return [item["sku"] for item in buscar_productos(consulta, CATALOGO)]

    def test_filtra_monitores(self):
        self.assertEqual(self.skus("monitores"), ["M1"])

    def test_no_confunde_notebook_ryzen_con_cpu(self):
        self.assertEqual(self.skus("procesadores ryzen"), ["C1"])

    def test_reconoce_gpu_amd_rx(self):
        self.assertEqual(self.skus("placas de video amd rx"), ["G1"])

    def test_excluye_sd_de_ram(self):
        self.assertEqual(self.skus("memorias ram ddr5"), ["R1"])

    def test_deduplica_sin_identificador_sin_perder_productos(self):
        catalogo = [
            producto(None, "", "Monitor A", "Monitores", "Monitor"),
            producto(None, "", "Monitor B", "Monitores", "Monitor"),
        ]
        self.assertEqual(
            [item["nombre"] for item in buscar_productos("monitor", catalogo)],
            ["Monitor A", "Monitor B"],
        )


if __name__ == "__main__":
    unittest.main()