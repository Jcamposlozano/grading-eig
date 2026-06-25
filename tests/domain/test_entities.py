from __future__ import annotations

from contenidos_inacap.domain.entities.actividad import Actividad
from contenidos_inacap.domain.entities.calificacion import Calificacion, ResultadoCriterio
from contenidos_inacap.domain.entities.curso import Curso
from contenidos_inacap.domain.entities.entregable import Entregable
from contenidos_inacap.domain.entities.estudiante import Estudiante
from contenidos_inacap.domain.entities.rubrica import CriterioRubrica, NivelRubrica, Rubrica
from contenidos_inacap.domain.entities.universidad import Universidad
from contenidos_inacap.domain.enums import ClasificacionActividad, EstadoEntregable


def test_hierarchy_construction():
    uni = Universidad(id="eig", nombre="EIG")
    curso = Curso(id="c1", universidad_id=uni.id, nombre="Curso 1")
    est = Estudiante(id="e1", universidad_id=uni.id, canvas_user_id="999")
    act = Actividad(
        id="a1", curso_id=curso.id, clasificacion=ClasificacionActividad.VIDEO, rubrica_id="r1"
    )

    assert curso.universidad_id == "eig"
    assert est.canvas_user_id == "999"
    assert act.clasificacion is ClasificacionActividad.VIDEO


def test_entregable_defaults():
    ent = Entregable(
        id="x",
        universidad_id="eig",
        curso_id="c1",
        estudiante_id="e1",
        actividad_id="a1",
        clasificacion=ClasificacionActividad.TEXTO,
    )

    assert ent.estado is EstadoEntregable.RECIBIDO
    assert ent.raw_key is None
    assert ent.created_at is not None


def test_rubrica_and_calificacion():
    rubrica = Rubrica(
        id="r1",
        max_score=10,
        criterios=[
            CriterioRubrica(
                id="c1",
                nombre="Crit",
                niveles=[NivelRubrica(nivel="Alto", puntos=10, descripcion="ok")],
            )
        ],
    )
    calificacion = Calificacion(
        entregable_id="x",
        total_score=10,
        publish=True,
        confidence=0.9,
        feedback_general="bien",
        resultados=[
            ResultadoCriterio(
                criterio_id="c1",
                criterio_nombre="Crit",
                nivel_seleccionado="Alto",
                puntos=10,
                justificacion="j",
            )
        ],
    )

    assert rubrica.criterios[0].niveles[0].puntos == 10
    assert calificacion.publish is True
    assert calificacion.publicado is False
