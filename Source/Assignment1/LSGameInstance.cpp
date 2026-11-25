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

void ULSGameInstance::RecordLevelResult(FName LevelName, const FLSLevelResult& Result)
{
	// Checked before FindOrAdd, which would make the level look finished. A first time of 0 must not count as a best.
	const bool bFirstFinish = !IsLevelFinished(LevelName);

	FLSLevelRecord& Record = LevelRecords.FindOrAdd(LevelName);
	Record.BestStars = FMath::Max(Record.BestStars, Result.Stars);
	Record.BestPetals = FMath::Max(Record.BestPetals, Result.PetalsCollected);
	Record.BestTimeSeconds = bFirstFinish ? Result.TimeSeconds : FMath::Min(Record.BestTimeSeconds, Result.TimeSeconds);

	SaveProgress();
}

int32 ULSGameInstance::GetTotalPetals() const
{
	int32 Total = 0;
	for (const TPair<FName, FLSLevelRecord>& Entry : LevelRecords)
	{
		Total += Entry.Value.BestPetals;
	}
	return Total;
}

void ULSGameInstance::SaveProgress()
{
	ULSSaveGame* Save = Cast<ULSSaveGame>(UGameplayStatics::CreateSaveGameObject(ULSSaveGame::StaticClass()));
	Save->UnlockedForms = UnlockedForms;
	// A new Level 1 run starts from Seed again; keep the forms earlier runs saved.
	if (const ULSSaveGame* Previous = Cast<ULSSaveGame>(UGameplayStatics::LoadGameFromSlot(SaveSlotName, SaveUserIndex)))
	{
		Save->UnlockedForms.Append(Previous->UnlockedForms);
	}
	Save->LevelRecords = LevelRecords;
	Save->MusicVolume = MusicVolume;
	Save->SfxVolume = SfxVolume;

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
		LevelRecords = Save->LevelRecords;
		MusicVolume = Save->MusicVolume;
		SfxVolume = Save->SfxVolume;
	}
}

void ULSGameInstance::DeleteProgress()
{
	UGameplayStatics::DeleteGameInSlot(SaveSlotName, SaveUserIndex);
	UnlockedForms = { ESeedForm::Seed };
	LevelRecords.Reset();
	MusicVolume = 1.f;
	SfxVolume = 1.f;
}
