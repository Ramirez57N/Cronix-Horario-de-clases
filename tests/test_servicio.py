import unittest
from datetime import datetime

from app import servicio as s
from app.db import conectar, iniciar_db


class PruebasHorario(unittest.TestCase):
    def setUp(self):
        self.conn = conectar(":memory:")
        iniciar_db(self.conn)
        self.ana = s.crear_catalogo(self.conn, "profesores", "Ana")["id"]
        self.luis = s.crear_catalogo(self.conn, "profesores", "Luis")["id"]
        self.mate = s.crear_catalogo(self.conn, "materias", "Matemáticas")["id"]
        self.g6a = s.crear_catalogo(self.conn, "grupos", "6A")["id"]
        self.g6b = s.crear_catalogo(self.conn, "grupos", "6B")["id"]
        self.s101 = s.crear_catalogo(self.conn, "salones", "101")["id"]
        self.s102 = s.crear_catalogo(self.conn, "salones", "102")["id"]
        self.f1 = s.crear_franja(self.conn, 1, "07:00", "08:00")["id"]
        self.f2 = s.crear_franja(self.conn, 2, "08:00", "09:00")["id"]

    def clase(self, prof, grupo, salon, dia=0, franja=None):
        return s.crear_clase(self.conn, self.mate, prof, grupo, salon, dia,
                             franja or self.f1)

    def test_crea_clase(self):
        c = self.clase(self.ana, self.g6a, self.s101)
        self.assertEqual(c["profesor"], "Ana")
        self.assertEqual(c["inicio"], "07:00")

    def test_choque_de_profesor(self):
        self.clase(self.ana, self.g6a, self.s101)
        with self.assertRaises(s.Conflicto):
            self.clase(self.ana, self.g6b, self.s102)

    def test_choque_de_grupo(self):
        self.clase(self.ana, self.g6a, self.s101)
        with self.assertRaises(s.Conflicto):
            self.clase(self.luis, self.g6a, self.s102)

    def test_choque_de_salon(self):
        self.clase(self.ana, self.g6a, self.s101)
        with self.assertRaises(s.Conflicto):
            self.clase(self.luis, self.g6b, self.s101)

    def test_mismo_recurso_en_otra_franja_es_valido(self):
        self.clase(self.ana, self.g6a, self.s101, franja=self.f1)
        self.clase(self.ana, self.g6a, self.s101, franja=self.f2)

    def test_actualizar_no_choca_consigo_misma(self):
        c = self.clase(self.ana, self.g6a, self.s101)
        nueva = s.actualizar_clase(self.conn, c["id"], self.mate, self.ana,
                                   self.g6a, self.s102, 0, self.f1)
        self.assertEqual(nueva["salon"], "102")

    def test_actualizar_con_choque(self):
        self.clase(self.ana, self.g6a, self.s101, franja=self.f1)
        c2 = self.clase(self.luis, self.g6b, self.s102, franja=self.f2)
        with self.assertRaises(s.Conflicto):
            # Ana ya da clase en f1; mover la clase de Luis a f1 con Ana choca
            s.actualizar_clase(self.conn, c2["id"], self.mate, self.ana,
                               self.g6b, self.s102, 0, self.f1)

    def test_profesores_libres(self):
        self.clase(self.ana, self.g6a, self.s101)
        libres = s.profesores_libres(self.conn, 0, self.f1)
        self.assertEqual([p["nombre"] for p in libres], ["Luis"])

    def test_estado_ahora(self):
        self.clase(self.ana, self.g6a, self.s101)
        lunes_730 = datetime(2026, 11, 2, 7, 30)  # lunes
        estado = s.estado_ahora(self.conn, lunes_730)
        self.assertEqual([c["profesor"] for c in estado["en_clase"]], ["Ana"])
        self.assertEqual([p["nombre"] for p in estado["libres"]], ["Luis"])

    def test_estado_ahora_fuera_de_horario(self):
        domingo = datetime(2026, 11, 8, 7, 30)
        self.assertEqual(s.estado_ahora(self.conn, domingo)["en_clase"], [])

    def test_validaciones(self):
        with self.assertRaises(s.ErrorDeNegocio):
            s.crear_franja(self.conn, 3, "10:00", "09:00")
        with self.assertRaises(s.NoEncontrado):
            s.crear_clase(self.conn, 99, self.ana, self.g6a, self.s101, 0, self.f1)
        with self.assertRaises(s.ErrorDeNegocio):
            s.crear_clase(self.conn, self.mate, self.ana, self.g6a, self.s101, 7, self.f1)


if __name__ == "__main__":
    unittest.main()
