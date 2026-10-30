// See LSGameInstance.h for this class's purpose and connections.

#include "LSGameInstance.h"

#include "Kismet/GameplayStatics.h"
#include "LSSaveGame.h"

namespace
{
	const TCHAR* const SaveSlotName = TEXT("LastSeedSave");
	constexpr int32 SaveUserIndex = 0;
}

void ULSGameInstance::Init()
{
	Super::Init();

	LoadProgress();
}

void ULSGameInstance::UnlockAllForms()
{
	UnlockForm(ESeedForm::Stone);
	UnlockForm(ESeedForm::Dandelion);
}

void ULSGameInstance::SetLastCheckpoint(const FString& LevelName, const FVector& Location)
{
	LastLevelName = LevelName;
	LastCheckpointLocation = Location;
}

void ULSGameInstance::SaveProgress()
{
	ULSSaveGame* Save = Cast<ULSSaveGame>(UGameplayStatics::CreateSaveGameObject(ULSSaveGame::StaticClass()));
	Save->UnlockedForms = UnlockedForms;
	Save->LastLevelName = LastLevelName;
	Save->LastCheckpointLocation = LastCheckpointLocation;

	if (!UGameplayStatics::SaveGameToSlot(Save, SaveSlotName, SaveUserIndex))
	{
		UE_LOG(LogTemp, Warning, TEXT("Last Seed: could not write the save file."));
	}
}

void ULSGameInstance::LoadProgress()
{
	// The cast also returns null when there is no save file yet, which is a normal first launch.
	const ULSSaveGame* Save = Cast<ULSSaveGame>(UGameplayStatics::LoadGameFromSlot(SaveSlotName, SaveUserIndex));
	if (Save)
	{
		// Append, not replace, so Seed stays unlocked even if a save file is damaged.
		UnlockedForms.Append(Save->UnlockedForms);
		LastLevelName = Save->LastLevelName;
		LastCheckpointLocation = Save->LastCheckpointLocation;
	}
}

void ULSGameInstance::DeleteProgress()
{
	UGameplayStatics::DeleteGameInSlot(SaveSlotName, SaveUserIndex);
	UnlockedForms = { ESeedForm::Seed };
	LastLevelName.Reset();
	LastCheckpointLocation = FVector::ZeroVector;
}
