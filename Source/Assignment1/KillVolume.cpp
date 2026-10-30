// See KillVolume.h for this class's purpose and connections.

#include "KillVolume.h"

#include "SeedBall.h"

void AKillVolume::OnBallOverlap(ASeedBall* Ball)
{
	Ball->Die();
}
