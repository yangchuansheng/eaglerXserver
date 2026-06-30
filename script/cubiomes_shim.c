#include <stdint.h>

#include "generator.h"
#include "finders.h"

typedef struct {
    int x;
    int z;
} CMPos;

typedef struct {
    int32_t salt;
    int8_t region_size;
    int8_t chunk_range;
    uint8_t struct_type;
    int8_t dim;
    float rarity;
} CMStructureConfig;

int cm_get_structure_config(int mc, int stype, CMStructureConfig *out)
{
    StructureConfig cfg;
    if (!out) {
        return 0;
    }
    if (!getStructureConfig(stype, mc, &cfg)) {
        return 0;
    }
    out->salt = cfg.salt;
    out->region_size = cfg.regionSize;
    out->chunk_range = cfg.chunkRange;
    out->struct_type = cfg.structType;
    out->dim = cfg.dim;
    out->rarity = cfg.rarity;
    return 1;
}

int cm_get_structure_pos(int mc, int stype, int64_t seed, int regx, int regz, CMPos *out)
{
    Pos pos;
    if (!out) {
        return 0;
    }
    if (!getStructurePos(stype, mc, (uint64_t) seed, regx, regz, &pos)) {
        return 0;
    }
    out->x = pos.x;
    out->z = pos.z;
    return 1;
}

int cm_is_structure_viable(int mc, int64_t seed, int stype, int x, int z, uint32_t flags)
{
    Generator g;
    setupGenerator(&g, mc, 0);
    applySeed(&g, DIM_OVERWORLD, (uint64_t) seed);
    return isViableStructurePos(stype, &g, x, z, flags);
}

int cm_get_spawn(int mc, int64_t seed, int approx, CMPos *out)
{
    Generator g;
    Pos pos;
    if (!out) {
        return 0;
    }
    setupGenerator(&g, mc, 0);
    applySeed(&g, DIM_OVERWORLD, (uint64_t) seed);
    pos = approx ? estimateSpawn(&g, 0) : getSpawn(&g);
    out->x = pos.x;
    out->z = pos.z;
    return 1;
}

int cm_get_strongholds(int mc, int64_t seed, int max_count, CMPos *out)
{
    Generator g;
    StrongholdIter iter;
    int written = 0;
    int remaining = 0;

    if (!out || max_count <= 0) {
        return 0;
    }

    setupGenerator(&g, mc, 0);
    applySeed(&g, DIM_OVERWORLD, (uint64_t) seed);
    initFirstStronghold(&iter, mc, (uint64_t) seed);

    while (written < max_count) {
        remaining = nextStronghold(&iter, &g);
        out[written].x = iter.pos.x;
        out[written].z = iter.pos.z;
        written++;
        if (remaining <= 0) {
            break;
        }
    }

    return written;
}
